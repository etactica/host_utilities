# signs up for notifications on a characteristic

Dumps a formatted "large" buffer via a batch of ATT_MTU sized notifications.
Accumulates the full set based on a simple "header" style of the first packet being three bytes, with a flag and a length,
then more packets til it's finished.

Works just fine.  however, like all of our bleak scripts so far, once this exits, you must powercycle the bluetooth adapter before it runs again :(

# TODO
* re-implement in https://github.com/getsenic/gatt-python (jpa has used this) (see https://github.com/PetteriAimonen/bletalk/blob/master/utils/connect.py)
* re-implement in ....? bleson? anything else? 
* Figure out what's wrong with bleak?
* what are we not closing properly?!
* Evaluate how fast we can continuously dump?  Is it feasible to dump entire sample buffers continuously?
