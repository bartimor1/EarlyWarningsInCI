# EarlyWarningsInCI
Detection of response time degradation in CI using process mining techniques on the software event logs.
This project demonstrating our thesis method for identifying and analyzing performance degradation due to code changes. 
The method receives two event logs as input: one is the execution log of the base version (before the code change) and the other is the execution log of the version under test (after the change). We assume that the two logs have undergone pre-processing and activity name matching to ensure accurate identification of events and traces.

## Prerequisite:
Ensure the following Python modules are installed before running the detection method:
* pandas
* numpy
* pm4py

## Configuration:
The labeling thresholds are defined in the cfg.py file. Modify this file to adjust the detection settings as needed.

## Running Performance Degradation Detection on Logs:
The main file executes the `detect.ipynb` method to analyze performance degradation.

If running the detection on simulation logs (txt files) generated using [EarlyWarningsSimulator](https://github.com/bartimor1/EarlyWarningsSimulator), ensure the following parameters are set in `detect:
* home_directory - Home directory where the simulation test cases are stored.
* scenario_group - Name of the simulated JSON scenarios folder.
* base_test_case_folder - Folder containing the simulated baseline scenario.
* test_case_folder - Folder containing the simulated performance degradation case.

Example configuration:
```
if simulation_mode:  
        scenario_group = "1_resilience_patterns"
        base_test_case_folder = "TC1_baseline_scenario"
        test_case_folder = "TC2_retry_due_to_high_level_operations_failures"
        home_directory = r"Path\To\Simulation\Test Cases"
        ...
```

If performing detection on your own logs, ensure they are in CSV format and contain the following columns:
* timestamp
* resource (component/module)
* req_id
* msg
* pid

Additionally, configure the following parameters:

**In cfg.ini:**
* simulation = False
* is_needed = False

**In detect.ipynb:**
* log_testcases_folder = The directory where the logs are stored
* event_log_b = The full path to the log before the change. 
* event_log_a = The full path to the log after the change.

**Note**: we assume that the two logs have undergone pre-processing and activity name matching to en-sure accurate identification of events and traces. These can be achieved by using approaches for parsing and mining log messages, e.g., SLCT, IPLoM, LKE, and LogSig 

To execute the detection, run the `detect.ipynb` file. The result report will be generated and stored in the `Results` folder.
