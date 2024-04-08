import threading
from multiprocessing import Pipe, Process, Queue
import re
import timeit
import psutil
import time
import random

# Globals
buffer = [] # For the inter-process communication

# Semaphores
mutex = threading.Semaphore(1)  # Mutex for buffer access
empty = threading.Semaphore(5)  # Semaphore for empty slots
data = threading.Semaphore(0)  # Semaphore for filled slots


def task_manager():
    while(True):
        print(
            "Select a mode.\n1. Search processes by name / print all processes\n2. See more information on a certain process (search by Process ID)\n3. Create a new process\n4. Suspend or resume a process (Process ID)\n5. Terminate a process\n6. Exit task control\nAs a warning, you cannot do some actions to certain processes, such as the system process.")
        search = input()

        if search == "1":
            search = input(
                "Enter in the name of a process. Type nothing for a list of all processes. ")  # Search for name

            for process in psutil.process_iter():
                if re.search(search, process.name()):
                    print(process)

        elif search == "2":
            search = input("Enter in the process ID of a process. ")

            for process in psutil.process_iter():
                if search == str(process.pid):
                    print(process)
                    print("\nAll parents")
                    for parent in process.parents():
                        print(parent)
                    print("\nAll children")
                    for child in process.children(recursive=True):
                        print(child)
                    print("\nProcess threads")
                    for thread in process.threads():
                        print(thread)

        elif search == "3":
            search = input("Input a process ID: ")
            if int(search) in psutil.pids():
                print("Error: Not a unique process ID")
            else:
                new_process = psutil.Process(int(search))

        elif search == "4":
            search = input(
                "Enter in the process ID of a process. If it is not suspended, it will be suspended. Otherwise, it will be resumed. ")

            for process in psutil.process_iter():
                if search == str(process.pid):
                    if process.is_running():
                        process.suspend()
                    else:
                        process.resume()

        elif search == "5":
            search = input(
                "Enter in the process ID of a process. It will be terminated. ")

            for process in psutil.process_iter():
                if search == str(process.pid):
                    process.terminate()

        elif search == "6":
            print("Exiting task control.")
            break
        else:
            print("No option selected.")


def IPC_process_shared():
    queue = Queue()

    def producer():
        for i in range(5):
            queue.put(i)

    def consumer():
        while not queue.empty():
            item = queue.get()
            print(item)

    producerp = Process(target=producer, args=(queue,))
    producerp.start()
    consumerp = Process(target=consumer, args=(queue,))
    consumerp.start()

    producerp.join()
    consumerp.join()

def IPC_thread_shared():
    # Shared buffer
    buffer = []

    # Semaphores
    mutex = threading.Semaphore(1)  # Mutex for buffer access
    empty = threading.Semaphore(10)  # Semaphore for empty slots
    data = threading.Semaphore(0)  # Semaphore for filled slots

    # Producer function
    def producer():
        for i in range(20):  # while True:
            item = random.randint(1, 100)  # Generate a random item
            empty.acquire()  # Wait for an empty slot
            mutex.acquire()  # Get exclusive access to the buffer
            buffer.append(item)  # Add item to the buffer
            print(f"Produced {item}. Buffer: {buffer}")
            mutex.release()  # Release the mutex
            data.release()  # Notify that a slot is filled
            time.sleep(random.uniform(0.1, 0.2))  # Simulate work

    # Consumer function
    def consumer():
        for i in range(10):  # while True:
            time.sleep(0.5)
            data.acquire()  # Wait for a filled slot
            mutex.acquire()  # Get exclusive access to the buffer
            item = buffer.pop(0)  # Remove and consume the first item
            print(f"Consumed {item}. Buffer: {buffer}")
            mutex.release()  # Release the mutex
            empty.release()  # Notify that a slot is empty

    # Create producer and consumer threads
    producers = [threading.Thread(target=producer) for _ in range(2)]

    consumers = [threading.Thread(target=consumer) for _ in range(4)]

    # Start the threads
    for producer_thread in producers:
        producer_thread.start()
    for consumer_thread in consumers:
        consumer_thread.start()

    # Allow the threads to run for some time
    time.sleep(5)

    # Terminate the threads (you would typically use a more graceful termination mechanism)
    for producer_thread in producers:
        producer_thread.join()
    for consumer_thread in consumers:
        consumer_thread.join()

def text_file_processing():
    letters_in_thread = [] # Tracker for the characters in the thread.
    num_letters = [] # Number of times a certain letter appears. Happens after capitalization.
    list_of_strings = [] # Buffer for the threads

    mutex = threading.Semaphore(1)  # Mutex for buffer access
    empty = threading.Semaphore(10000)  # Semaphore for empty slots
    data = threading.Semaphore(0)  # Semaphore for filled slots

    def letter_add(c): # Not a process, but a function.
        if c in letters_in_thread:
            i = 0
            while c != letters_in_thread[i]:
                i+=1
            num_letters[i] += 1
        else:
            letters_in_thread.append(c)
            num_letters.append(1)

    def reader_thread(file): # Thread that will read the file
        big_string = file
        i = 0
        while len(big_string) > (i * 50):
            snippet = len(big_string) - (i * 50)
            if snippet >= 50:
                empty.acquire()  # Wait for an empty slot
                mutex.acquire()  # Get exclusive access to the buffer
                list_of_strings.append(big_string[(0 + 50 * i):(50 + 50 * i)])  # Add item to the buffer
                i+=1
                mutex.release()  # Release the mutex
                data.release()  # Notify that a slot is filled
            else:
                empty.acquire()  # Wait for an empty slot
                mutex.acquire()  # Get exclusive access to the buffer
                list_of_strings.append(big_string[(0 + 50 * i):])  # Add item to the buffer
                i+=1
                mutex.release()  # Release the mutex
                data.release()  # Notify that a slot is filled

    def consumer_thread(): # Thread that processes the data that is being read
        while len(list_of_strings) > 0:
            processed_string = list_of_strings.pop()
            for char in processed_string:
                char = str.upper(char)
                letter_add(char)

    consumers = [threading.Thread(target=consumer_thread) for _ in range(2)]

    file = input("Put the full file directory here: ")
    time_taken = timeit.default_timer()
    file = open(file, "r")
    file = file.readlines()
    file = ''.join(file).replace('\n', '')
    reader = threading.Thread(target=reader_thread, args=(file,))
    reader.start()
    reader.join()
    print("Reader has finished")
    for consumer_thread in consumers:
        consumer_thread.start()

    for consumer_thread in consumers:
        consumer_thread.join()

    i = 0
    count = 0
    for letter in letters_in_thread:
        print(letter + " appeared " + str(num_letters[i]) + " times.")
        count += num_letters[i]
        i+=1
    print("There were " + str(count) + " characters in the file.")
    time_taken_2 = timeit.default_timer()
    print("Total execution time: " + str(time_taken_2 - time_taken) + " seconds")
    print("CPU usage: " + str(psutil.cpu_percent()) + "%")
    print("Memory usage: " + str(psutil.virtual_memory()) + "%")

def main_menu():
    while True:
        choice = input("What mode do you want to use?\n1. Process task manager\n2. IPC Comparison\n3. Text file processor\n4. Exit program ")
        if choice == "1":
            task_manager()
        elif choice == "2":
            # IPC_process_shared()
            IPC_thread_shared()
            print("The feature is not fully completed.")
            print("Due to problems with the multiprocessing module, this feature is unfortunately canceled.")
        elif choice == "3":
            text_file_processing()
        elif choice == "4":
            break
        else:
            print("Not a valid command, try again.")

main_menu()