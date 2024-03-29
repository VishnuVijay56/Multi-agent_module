#!/usr/bin/env python

__author__ = "Vishnu Vijay"
__contact__ = "@purdue.edu"

import argparse
import sys

import rclpy
import numpy as np
from functools import partial

from rclpy.node import Node
from rclpy.clock import Clock
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy
import navpy

from px4_msgs.msg import VehicleLocalPosition, VehicleAttitude

from geometry_msgs.msg import PointStamped, TransformStamped
from std_msgs.msg import UInt8, Bool, Float32MultiArray

from tf2_ros import TransformBroadcaster


class DynamicFramesBroadcaster(Node):

    def __init__(self, num_drones):

        super().__init__("dynamic_frames_tf2_broadcaster")

        # Node Parameters
        self.num_drones = num_drones
        self.pos_ned = [None] * num_drones # these will be wrt original drone 1 pos


        # set publisher and subscriber quality of service profile
        qos_profile_pub = QoSProfile(
            reliability = QoSReliabilityPolicy.BEST_EFFORT,
            durability = QoSDurabilityPolicy.TRANSIENT_LOCAL,
            history = QoSHistoryPolicy.KEEP_LAST,
            depth = 1
        )

        qos_profile_sub = QoSProfile(
            reliability = QoSReliabilityPolicy.BEST_EFFORT,
            durability = QoSDurabilityPolicy.VOLATILE,
            history = QoSHistoryPolicy.KEEP_LAST,
            depth = 5
        )


        # Define subscribers and publishers
        self.local_pos_sub = [None] * num_drones
        self.local_att_sub = [None] * num_drones
        self.tf_broadcaster = [None] * num_drones
        self.transform = [None] * num_drones
        for i in range(num_drones):
            sub_pos_topic_name = "/px4_" + str(i+1) + "/fmu/out/vehicle_local_position"
            self.local_pos_sub[i] = self.create_subscription(
                VehicleLocalPosition,
                sub_pos_topic_name,
                partial(self.local_position_callback, drone_ind=i),
                qos_profile_sub)
            
            sub_att_topic_name = "/px4_" + str(i+1) + "/fmu/out/vehicle_attitude"
            self.local_att_sub[i] = self.create_subscription(
                VehicleAttitude,
                sub_att_topic_name,
                partial(self.local_attitude_callback, drone_ind=i),
                qos_profile_sub)
            
            self.tf_broadcaster[i] = TransformBroadcaster(self)

            self.transform[i] = TransformStamped()
            self.transform[i].header.frame_id = "drone_" + str(i + 1) + "_origin"
            self.transform[i].child_frame_id = "drone_" + str(i + 1) + "_pos"



    ### Subscriber callbacks
        
    def local_position_callback(self,msg,drone_ind):
        try:
            self.transform[drone_ind].header.stamp = self.get_clock().now().to_msg()
            self.transform[drone_ind].transform.translation.x = msg.x
            self.transform[drone_ind].transform.translation.y = msg.y
            self.transform[drone_ind].transform.translation.z = msg.z

            self.tf_broadcaster[drone_ind].sendTransform(self.transform[drone_ind])

        except:
            self.get_logger().info("Exception: Issue with getting position of drone #" + str(drone_ind))


    def local_attitude_callback(self,msg,drone_ind):
        try:
            self.transform[drone_ind].header.stamp = self.get_clock().now().to_msg()
            self.transform[drone_ind].transform.rotation.x = msg.q[0]
            self.transform[drone_ind].transform.rotation.y = msg.q[1]
            self.transform[drone_ind].transform.rotation.z = msg.q[2]
            self.transform[drone_ind].transform.rotation.w = -msg.q[3]

            self.tf_broadcaster[drone_ind].sendTransform(self.transform[drone_ind])

        except:
            self.get_logger().info("Exception: Issue with getting attitude of drone #" + str(drone_ind))

### Main Func
    
def main():

    # Parse Arguments
    main_args = sys.argv[1:]
    num_drones = 1
    if (len(main_args) == 2) and (main_args[0] == "-n"):
        num_drones = int(main_args[1])
    
    # Node init
    rclpy.init(args=None)
    positions_broadcaster = DynamicFramesBroadcaster(num_drones=num_drones)
    positions_broadcaster.get_logger().info("Initialized")

    # Spin Node
    rclpy.spin(positions_broadcaster)

    # Explicitly destroy node
    positions_broadcaster.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':

    main()