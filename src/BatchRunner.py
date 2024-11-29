import os.path
import papermill as pm
from lib.utils import get_test_case_directory

if __name__ == '__main__':

    [_, logs_home_dir] = get_test_case_directory("Path/To/Test/Cases/Folder", True)
    scenario_groups = [group for group in os.listdir(logs_home_dir) if os.path.isdir(os.path.join(logs_home_dir, group))]


    print(f"Running on the following scenario groups {scenario_groups}")


    for scenario_group in scenario_groups:
        """
        For each scenario group, run analysis on all individual scenarios.
        """
        results_dir = os.path.join("../results/", scenario_group)
        os.makedirs(results_dir, exist_ok=True)

        for testcase_name in os.listdir(os.path.join(logs_home_dir, scenario_group)):
            if testcase_name == 'Results':
                continue

            # Do not compare the baseline against itself
            if testcase_name == "TC1_baseline_scenario":
                continue

            # Run model
            print(f"Executing test case {testcase_name}")
            pm.execute_notebook(
                'detect.ipynb',
                f'{results_dir}/output_{testcase_name}.ipynb',
                parameters=dict(scenario_group=scenario_group, test_case_folder=testcase_name)
            )