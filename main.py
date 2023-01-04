import os
import sys
path = os.path.dirname(os.path.abspath(__file__))
print(path)
sys.path.insert(0, path)


from src import network_T1
from src import network_T2
from src import network_T3




if __name__ == '__main__':
    network = input("Enter the type of network you want to create: ")
    if network == "T1":
        network_T1.networkT1_main()
    elif network == "T2":
        network_T2.networkT2_main()
    elif network == "T3":
        network_T3.networkT3_main()


