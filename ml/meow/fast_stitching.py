import os
import sys
ROOT_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(ROOT_FOLDER)
sys.path.append("build/")
from SumLib import SumClass

sum = SumLib(2, 3)
sum_value = sum.run()
print(sum_value)