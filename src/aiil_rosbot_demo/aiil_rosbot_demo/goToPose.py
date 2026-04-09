#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped

class GoToPose(Node):
    def __init__(self):
        super().__init__('navigation_goal_publisher')
        self.publisher_ = self.create_publisher(PoseStamped, 'goal_pose', 10)
        self.timer = self.create_timer(10.0, self.publish_goal)
        self.goal_pose = PoseStamped()

        # Set your desired goal position and orientation here
        self.goal_pose.header.frame_id = 'map'
        self.goal_pose.pose.position.x = 1.0
        self.goal_pose.pose.position.y = -2.0
        self.goal_pose.pose.position.z = 0.0
        self.goal_pose.pose.orientation.x = 0.0
        self.goal_pose.pose.orientation.y = 0.0
        self.goal_pose.pose.orientation.z = 0.0
        self.goal_pose.pose.orientation.w = 1.0

    def publish_goal(self):
        self.goal_pose.header.stamp = self.get_clock().now().to_msg()
        self.publisher_.publish(self.goal_pose)
        self.get_logger().info('Publishing Navigation Goal: x=%f, y=%f' % (self.goal_pose.pose.position.x, self.goal_pose.pose.position.y))

def main(args=None):
    rclpy.init(args=args)
    navigation_goal_publisher = GoToPose()
    rclpy.spin(navigation_goal_publisher)
    navigation_goal_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()