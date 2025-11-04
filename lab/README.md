# Lab: Postgres+Patroni cluster

## Cheatsheet
```
./session_start.sh  Start interactive tmux session with all cluster nodes
./psql.sh           Start psql client to whole cluster
./automation_*      Start/stop orchestrator reconciliation
./case_*            Apply some changes to cluster for study purposes
./pgbench_*         Generate/Run pgbench tests

patronictl:
  edit-config       Edit cluster configuration
  failover          Failover to a replica
  history           Show the history of failovers/switchovers
  list              List the Patroni members for a given Patroni
  reinit            Reinitialize cluster member
  restart           Restart cluster member
  show-config       Show cluster configuration
  switchover        Switchover to a replica
  topology          Prints ASCII topology for given cluster
```

## Presentation
You can find whole presentation [here (RU)](https://bit.ly/hl_dbaas).

## **Hands-On Case Studies**

This is a list of practical cases to understand the operation and failure scenarios of a 3-node Patroni-managed PostgreSQL cluster.

**Initial State:** A 3-node cluster with 1 primary and 2 synchronous replicas.

---
**Note:** use `./start_session.sh` to get easy-to-use work space (tmux session).

**Case 0: Initial Setup & Verification**
*   Verify a 3-node cluster is running with 2 synchronous replicas.
*   Check the status using `patronictl list`.

**Case 1: Break and Fix the Configuration**

*   Intentionally break the Patroni configuration file (e.g., `patroni.yml`) on one node (see `./case_1.sh`).
*   Observe the cluster's state and error logs.
*   Review the structure and key parameters of the `patroni.yml` configuration file.
*   Fix the configuration and restore the node to the cluster.
*   Or - just restart automation: `./automation_start.sh`.

**Graceful Switchover**
*   Perform a planned switchover to promote a replica to primary using `patronictl switchover`.
*   Observe the failover process and update of the cluster leader.
*   **Reset:** After each case, return the primary role to the initial node (where the client is).

**Case 2: Data Corruption on the Primary**
*   Simulate data corruption on the primary node's database (see `./case_2_corrupt_data.sh`).
*   Observe: The cluster will not automatically failover as it's not a node failure.
*   Show that a simple Patroni restart does not resolve the data corruption.
*   Look into `patronictl reinit` command as the tool to re-sync a corrupted node by re-cloning data from a healthy node or backup.

**Case 3: Application Connectivity and Performance**
*   **Connection:** Try how an application connects to the cluster using a script like `./psql.sh` that leverages Patroni's REST API to find the leader.
*   **Performance:** Run performance tests using `./pgbench_generate_data.sh` + `./pgbench_run.sh`.
*   **Network Latency:** Artificially increase network latency (see `case_3.1_add_latency.sh`) and re-run `pgbench` tests to observe the impact on transaction performance and replication lag.
*   Remove network latency (see `./case_3.2_remove_latency.sh`)

**Case 4: Switching a Node to Asynchronous Replication**
*   Use `patronictl edit-config` to modify the cluster configuration.
*   Change `synchronous_node_count` to 1
*   Verify the change and observe the behavior difference.
*   Find the problem if parameter didn't changed (don't forget about automation existence!)

**Case 5: Network Partition (Split-Brain Scenario)**
*   Simulate a network failure on one node, isolating it from the rest of the cluster.
*   Observe how the remaining nodes form a quorum and elect a new leader.
*   Monitor the state of the isolated node.
*   Restore the network and observe the node's re-joining process.

**Case 6: Bring your own Case**
*   We'd be glad to hear any interesting cases from you via issues/PRs!

**Case 7: (Optional) Simulating a Disk Failure**
*   Dramatically "remove" a disk from a server (e.g., by unmounting a filesystem or using a fault injection tool, or physically).
*   *Optional prop: Bring a hammer for a humorous effect.*
*   Observe how the cluster handles the complete loss of a node's data disk.
