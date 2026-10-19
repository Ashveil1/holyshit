import sys; sys.path.insert(0,'.')
import lib
T=['add','sub','mul1']
lib.run_set(T,6,(),'raw6 (no library)')
lib.run_set(T,6,(('%','10'),('//','10')),'lib6 (mined %10, //10)')
