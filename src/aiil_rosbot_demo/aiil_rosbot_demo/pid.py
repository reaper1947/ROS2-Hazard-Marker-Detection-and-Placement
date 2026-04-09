#!/usr/bin/env python  

import rclpy
from rclpy.node import Node

import geometry_msgs.msg
import tf2_geometry_msgs
import tf2_ros

import numpy as np

class PID(Node):
    def __init__(self):
        super().__init__('aiil_pid')
        
        # Define Parameters
        self.declare_parameters(
            namespace='',
            parameters=[
                ('duration', 10),
                ('gain_p', 1.5),
                ('gain_i', 0),
                ('gain_d', 0),
                ('set_point', 1.5),
                ('max_speed', 2.0)
            ]
        )
        
        # Look-up parameters values
        self.duration = self.get_parameter('duration').value
        self.gain_p = self.get_parameter('gain_p').value
        self.gain_i = self.get_parameter('gain_i').value
        self.gain_d = self.get_parameter('gain_d').value
        self.max_speed = self.get_parameter('max_speed').value
        self.set_point = self.get_parameter('set_point').value
        
        # Frame configuration
        self.frame_robot = "base_link"
        self.frame_odom = "odom"
        
        # PID Error tracking
        self.error = 0
        self.error_sum = 0
        self.error_diff = 0
        self.previous_error = 0
        self.stop = False
        
        # Transform listener
        self.tf_buffer = tf2_ros.buffer.Buffer()
        self.tf_listener = tf2_ros.transform_listener.TransformListener(self.tf_buffer, self)
        
        # Command Velocity Publisher
        self.topic = "/cmd_vel"
        self.pub = self.create_publisher(geometry_msgs.msg.Twist, self.topic, 10)
        
        # Setup timer callback
        self.timer = self.create_timer(1.0, self.pidLoop)
    
    # Taken from: https://gist.github.com/salmagro/2e698ad4fbf9dae40244769c5ab74434
    # This method is no longer available in TF2 see: https://github.com/ros/geometry2/issues/222
    # So we have to compute the transformation by hand
    def euler_from_quaternion(self, quaternion):
        x = quaternion.x
        y = quaternion.y
        z = quaternion.z
        w = quaternion.w

        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = np.arctan2(sinr_cosp, cosr_cosp)

        sinp = 2 * (w * y - z * x)
        pitch = np.arcsin(sinp)

        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = np.arctan2(siny_cosp, cosy_cosp)

        return roll, pitch, yaw
    
    def pidLoop(self):
        
        # If set-point reached - stop
        if not self.stop:
            try:
                time = self.get_clock().now() - rclpy.duration.Duration(seconds=0.1)
                self.get_logger().info("--------------------------------")
                self.get_logger().info("Time:" + str(time))

                # Timeout for transform data
                timeout = rclpy.duration.Duration(seconds=1.00)
                
                # Lookup a transform
                transform = self.tf_buffer.lookup_transform(self.frame_odom, self.frame_robot, time, timeout=timeout)
                self.get_logger().info(f"Transform: {transform.transform}")
                
                # Apply a transform that has been retrieved from the buffer
                pose = geometry_msgs.msg.Pose()
                pose.position.x = 0.0
                pose.position.y = 0.0
                pose.position.z = 0.0
                pose.orientation.x = 0.0
                pose.orientation.y = 0.0
                pose.orientation.z = 0.0
                pose.orientation.w = 1.0
                poseOdom = tf2_geometry_msgs.do_transform_pose(pose, transform)
                self.get_logger().info(f" - Odometry Pose is: {poseOdom}")
    
                # Convert the Quaternion to roll,pitch-yaw
                (roll, pitch, yaw) = self.euler_from_quaternion(poseOdom.orientation)

                # Compute PID
                self.error = self.set_point - yaw
                self.error_sum += self.error
                self.error_diff = self.error - self.previous_error
                self.previous_error = self.error
                #rot_cmd = gain_p * error
                rot_cmd = self.gain_p * self.error + \
                        self.gain_i * self.error_sum + \
                        self.gain_d * self.error_diff
                self.get_logger().info(f"Error: {rot_cmd}")

                # Clip speed
                rot_cmd = min(rot_cmd, self.max_speed)
                rot_cmd = max(rot_cmd, -self.max_speed)

                # Setup Twist message
                cmd_vel = geometry_msgs.msg.Twist()
                cmd_vel.angular.z = rot_cmd
                
                # Publish
                self.get_logger().info(f"Sending command: {cmd_vel}")
                self.pub.publish(cmd_vel)
                
                # Check time
                # t_now = rospy.Time.now()
                # duration = t_now - t_start
                # if t_now - t_start > rospy.Duration(max_duration):
                #     stop = True
            except tf2_ros.TransformException as ex:
                self.get_logger().info(f'Could not transform {self.frame_robot} to {self.frame_odom}: {ex}')

        else:
            self.get_logger().info("--------------------------------")
            self.get_logger().info("Set point reached")

        # # Update velocities
        # self.driveSpeed = -1 * self.driveSpeed

def main():
    rclpy.init()
    node = PID()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    rclpy.shutdown()
    exit(0)


