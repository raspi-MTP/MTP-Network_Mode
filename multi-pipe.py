import time
import multiprocessing

def sleeper(pipe):
    out_p, in_p = pipe
    out_p.close()           # Only writing
    time.sleep(2.5)
    in_p.send("Child awake!")
    in_p.close()
    return 0

start_time = time.time()

out_p, in_p = multiprocessing.Pipe()
p = multiprocessing.Process(target=sleeper, args=((out_p, in_p),))
p.start()
in_p.close()                # Only reading
p.join(2)
end_time = time.time()
print("Parent awake! Total time = " + "%.6f"%(end_time-start_time) + " s")

while p.is_alive():
    time.sleep(0.5)

read_str = out_p.recv()
out_p.close()
print(str(read_str))
# p.terminate()
