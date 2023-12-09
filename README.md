## CSE138_Assignment3

# Mechanism Description

The system tracks causal dependencies using a vector clock. Whenever a replica does a job, it increments its index in the vector clock by one. This update is then eventually spread to other replicas. After some time, all replicas will stabilize and converge to a shared state.

The system can detect a replica going down by not hearing a response from it after multiple retries.

# Team Contributions
Created by Seth Stone, Andrew Song, and Hao Tran.
We all worked equally on the assignment, meeting together to code it together.

# Acknowledgements
N/A

# Citations
https://flask.palletsprojects.com/en/3.0.x/
https://requests.readthedocs.io/en/latest/
https://pyphi.readthedocs.io/en/latest/api/jsonify.html

# Notes
The assignment is not fully working. We located that the issue was the replicas were not able to properly keep track of a peer replica when it was put into view via putVIEW. We are unsure why this is the case and struggled to debug the issue becaue we could not see the outputs from the replica when the replica was spawned via docker.