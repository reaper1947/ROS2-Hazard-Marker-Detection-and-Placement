#!/usr/bin/env python

import math
import rclpy
import rclpy.duration
import rclpy.qos
from rclpy.node import Node

import tf2_ros
import tf2_geometry_msgs

import geometry_msgs.msg
from std_msgs.msg import Float32MultiArray, Empty, String
from sensor_msgs.msg import LaserScan
from visualization_msgs.msg import Marker

HAZARD_ID_MAP = {
    0: "Unknown",
    1: "Explosive",
    2: "Flammable Gas",
    3: "Non-Flammable Gas",
    4: "Dangerous When Wet",
    5: "Flammable Solid",
    6: "Spontaneously Combustible",
    7: "Oxidizer",
    8: "Organic Peroxide",
    9: "Inhalation Hazard",
    10: "Poison",
    11: "Radioactive",
    12: "Corrosive",
}

START_MARKER_OBJECT_ID = 13
DUPLICATE_DISTANCE_THRESHOLD = 0.5
DETECTION_CONFIRM_FRAMES = 3
CAMERA_HFOV_DEG = 69.0
CAMERA_IMAGE_WIDTH = 640.0


class HazardDetector(Node):
    def __init__(self):
        super().__init__("hazard_detector")

        self.declare_parameters(
            namespace="",
            parameters=[
                ("hfov_deg", CAMERA_HFOV_DEG),
                ("image_width", CAMERA_IMAGE_WIDTH),
                ("duplicate_threshold", DUPLICATE_DISTANCE_THRESHOLD),
                ("confirm_frames", DETECTION_CONFIRM_FRAMES),
                ("publish_rate", 1.0),
            ],
        )

        self.hfov = math.radians(self.get_parameter("hfov_deg").value)
        self.image_width = self.get_parameter("image_width").value
        self.dup_threshold = self.get_parameter("duplicate_threshold").value
        self.confirm_frames = int(self.get_parameter("confirm_frames").value)
        publish_rate = self.get_parameter("publish_rate").value

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.laser_ranges = []
        self.laser_angle_min = 0.0
        self.laser_angle_increment = 0.0
        self.laser_range_max = 10.0

        self.confirmed_hazards = {}
        self.pending_detections = {}

        self.create_subscription(
            Float32MultiArray,
            "/objects",
            self.objects_callback,
            10,
        )

        self.create_subscription(
            LaserScan,
            "/scan",
            self.laser_callback,
            rclpy.qos.qos_profile_sensor_data,
        )

        self.hazard_pub = self.create_publisher(Marker, "/hazards", 10)
        self.status_pub = self.create_publisher(String, "/snc_status", 10)

        self.republish_timer = self.create_timer(publish_rate, self.republish_confirmed)

        self.get_logger().info("HazardDetector node started.")

    # -----------------------------------------------------------------------
    # Sensor callbacks
    # -----------------------------------------------------------------------

    def laser_callback(self, msg: LaserScan):
        self.laser_ranges = list(msg.ranges)
        self.laser_angle_min = msg.angle_min
        self.laser_angle_increment = msg.angle_increment
        self.laser_range_max = msg.range_max

    def objects_callback(self, msg: Float32MultiArray):
        data = msg.data
        if len(data) == 0:
            return

        i = 0
        while i + 11 < len(data):
            object_id = int(data[i])
            img_width = data[i + 1]
            # img_height = data[i + 2]  (unused but present in the array)
            # homography h0..h8 = data[i+3 .. i+11]
            h = data[i + 3: i + 12]
            i += 12

            if object_id == START_MARKER_OBJECT_ID:
                continue

            if object_id not in HAZARD_ID_MAP:
                self.get_logger().warn(f"Unknown object id {object_id}, skipping.")
                continue

            bbox_center_x = img_width / 2.0
            map_point = self.estimate_map_position(bbox_center_x)
            if map_point is None:
                continue

            self.accumulate_detection(object_id, map_point.x, map_point.y)

    # -----------------------------------------------------------------------
    # Position estimation
    # -----------------------------------------------------------------------

    def estimate_map_position(self, bbox_center_x: float):
        angle_from_center = (
            (bbox_center_x - self.image_width / 2.0) / self.image_width * self.hfov
        )

        distance = self.get_laser_distance(angle_from_center)
        if distance is None:
            return None

        x_base = distance * math.cos(angle_from_center)
        y_base = distance * math.sin(angle_from_center)

        return self.transform_to_map(x_base, y_base)

    def get_laser_distance(self, angle: float):
        if len(self.laser_ranges) == 0:
            self.get_logger().warn("No laser data yet.")
            return None

        idx = int(
            (angle - self.laser_angle_min) / self.laser_angle_increment
        )
        idx = max(0, min(idx, len(self.laser_ranges) - 1))

        dist = self.laser_ranges[idx]

        if math.isinf(dist) or math.isnan(dist) or dist <= 0.05:
            return None

        return dist

    def transform_to_map(self, x: float, y: float):
        try:
            pose = geometry_msgs.msg.PoseStamped()
            pose.header.frame_id = "base_link"
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.pose.position.x = x
            pose.pose.position.y = y
            pose.pose.position.z = 0.0
            pose.pose.orientation.w = 1.0

            transformed = self.tf_buffer.transform(
                pose, "map", timeout=rclpy.duration.Duration(seconds=0.1)
            )
            return transformed.pose.position

        except tf2_ros.TransformException as ex:
            self.get_logger().warn(f"TF transform failed: {ex}")
            return None

    # -----------------------------------------------------------------------
    # Detection confirmation (debounce)
    # -----------------------------------------------------------------------

    def accumulate_detection(self, object_id: int, x: float, y: float):
        if object_id not in self.pending_detections:
            self.pending_detections[object_id] = {"x": x, "y": y, "count": 1}
            return

        entry = self.pending_detections[object_id]
        dist = math.sqrt((x - entry["x"]) ** 2 + (y - entry["y"]) ** 2)

        if dist < self.dup_threshold:
            # Running average position + increment count
            n = entry["count"]
            entry["x"] = (entry["x"] * n + x) / (n + 1)
            entry["y"] = (entry["y"] * n + y) / (n + 1)
            entry["count"] += 1
        else:
            # Position jumped too far — reset
            self.pending_detections[object_id] = {"x": x, "y": y, "count": 1}
            return

        if entry["count"] >= self.confirm_frames:
            self.confirm_hazard(object_id, entry["x"], entry["y"])
            del self.pending_detections[object_id]

    def confirm_hazard(self, object_id: int, x: float, y: float):
        if self.is_duplicate(object_id, x, y):
            return

        self.confirmed_hazards[object_id] = (x, y)
        self.publish_hazard_marker(object_id, x, y)

        name = HAZARD_ID_MAP.get(object_id, "Unknown")
        self.get_logger().info(
            f"Confirmed hazard [{object_id}] {name} at map ({x:.2f}, {y:.2f})"
        )
        self.publish_status(
            f"Detected hazard: {name} at ({x:.2f}, {y:.2f}). "
            f"Total found: {len(self.confirmed_hazards)}/5"
        )

    def is_duplicate(self, object_id: int, x: float, y: float) -> bool:
        if object_id in self.confirmed_hazards:
            ex, ey = self.confirmed_hazards[object_id]
            dist = math.sqrt((x - ex) ** 2 + (y - ey) ** 2)
            return dist < self.dup_threshold
        return False

    # -----------------------------------------------------------------------
    # Publishing
    # -----------------------------------------------------------------------

    def publish_hazard_marker(self, hazard_id: int, x: float, y: float):
        marker = Marker()
        marker.header.frame_id = "map"
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "hazards"
        marker.id = hazard_id
        marker.type = Marker.SPHERE
        marker.action = Marker.ADD

        marker.pose.position.x = x
        marker.pose.position.y = y
        marker.pose.position.z = 0.0
        marker.pose.orientation.x = 0.0
        marker.pose.orientation.y = 0.0
        marker.pose.orientation.z = 0.0
        marker.pose.orientation.w = 1.0

        marker.scale.x = 0.3
        marker.scale.y = 0.3
        marker.scale.z = 0.3

        marker.color.r = 1.0
        marker.color.g = 0.2
        marker.color.b = 0.0
        marker.color.a = 1.0

        marker.lifetime.sec = 0  # Persist forever

        self.hazard_pub.publish(marker)

    def republish_confirmed(self):
        for hazard_id, (x, y) in self.confirmed_hazards.items():
            self.publish_hazard_marker(hazard_id, x, y)

    def publish_status(self, text: str):
        msg = String()
        msg.data = text
        self.status_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = HazardDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
