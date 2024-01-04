import os
import struct
import numpy as np
import socket
import time

def acquire_data_from_rp(
    parallel_func_loop_count,
    buffer_size,
    shared_time,
    shared_prediction,
    shared_array,
    shared_child_pid,
    event_p1_for_sync,
    event_p2_for_sync,
    event_waiting_for_prediciton_result,
):
    shared_child_pid.value = os.getpid()

    # send cmd to redpitaya server
    socket_object = send_cmd_to_redpitaya()

    # Variable to keep track of loop count

    # Waiting for the event to set
    run_while_loop = event_p1_for_sync.wait(15)
    a = run_while_loop

    while run_while_loop:
        print(
            f"Inside acquire data++++{shared_child_pid.value}+++++++++++ : {parallel_func_loop_count}  : {shared_time.value}"
        )
        # update loop_count
        parallel_func_loop_count += 1
        packet = socket_object.recv(buffer_size)

        print("Waiting for prediction to complete from US ")
        if event_waiting_for_prediciton_result.wait(15):
            event_waiting_for_prediciton_result.clear()
            #print("Event Prediction wait for 15 sec and is cleared in US")
            print("Waiting Done.!!!")
        else:
            break

        # region saving the received bytes and encoding
        current_time = time.strftime("%Y %m %d")
        file_name = f"{current_time}_{parallel_func_loop_count}_{shared_time.value}_{shared_prediction.value}_adc.csv"

        if shared_prediction.value == "p":
            folder_name = "experiments/binaries/person/"
        else:
            folder_name = "experiments/binaries/noperson/"
       
        # Save data to CSV
        np.savetxt(
            f"{folder_name}{file_name}",
            np.array(shared_array).reshape(1,-1),  # Reshape only if necessary
            fmt="%d",  # Format specifier for integers
            delimiter=",",  # Use comma as the delimiter
            #comments="",  # Avoid adding comments to the header
        )

        for index, data in enumerate(struct.iter_unpack("@h", packet[64:])):
            shared_array[index] = data[0]

        # endregion

        # for syncing
        event_p2_for_sync.set()
        print('p2 is set in US')
        if event_p1_for_sync.wait(15):
            event_p1_for_sync.clear()
            #print("Event P1 for sync.clear US and start while of US")
            run_while_loop = True
        else:
            print("Exiting parallel function")
            run_while_loop = False


def send_cmd_to_redpitaya(cmd="-a 1"):
    socket_object = get_socket_object()
    server_address_port = ("192.168.128.1", 61231)
    msg_from_client = cmd
    bytes_to_send = str.encode(msg_from_client)
    socket_object.sendto(bytes_to_send, server_address_port)
    return socket_object


def get_socket_object():
    server_address_port = ("192.168.128.1", 61231)
    # Create a UDP socket at client side
    socket_obj = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    return socket_obj


def stop_socket(socket_object):
    socket_object.close()
