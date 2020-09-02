import os
import inspect

from fabric.api import task, local, cd, env, shell_env
from fabric.context_managers import hide, settings

env.use_ssh_config = True


@task(default=True)
def local_deploy(system_uuid="0000", stream_name="test-stream", stream=None):
    """
    Deploys a stream with the given parameters locally
    :param system_uuid: UUID of the system - unique RAMI 4.0 station
    :param stream_name: name of the stream app
    :param stream: attribute dictionary for stream with keys SOURCE_SYSTEM, TARGET_SYSTEM,
    KAFKA_BOOTSTRAP_SERVERS, GOST_SERVER, and FILTER_LOGIC
    :return:
    """
    # run('git clone https://git-service.ait.ac.at/im-IoT4CPS/WP5-lifecycle-mgmt.git /WP5-lifecycle-mgmt')
    # local('docker-compose -f ../StreamHub/docker-compose.yml up --build -d')

    with cd('../../StreamHub'):
        # image name is 'iot4cps/streamapp', container_name is the container name
        with hide('output', 'running'), settings(warn_only=True):
            local('docker build -t iot4cps/streamengine .')

        container_name = build_name(system_uuid, stream_name)
        if stream is None:  # fill with test values if emptystream = dict()
            print("WARNING, no parameter given.")
            stream = dict()
            stream["SOURCE_SYSTEM"] = "is.iceland.iot4cps-wp5-WeatherService.Stations"
            stream["TARGET_SYSTEM"] = "cz.icecars.iot4cps-wp5-CarFleet.Car1"
            stream["KAFKA_BOOTSTRAP_SERVERS"] = "127.0.0.1:9092"
            stream["GOST_SERVER"] = "127.0.0.1:8082"
            stream["FILTER_LOGIC"] = \
                "SELECT * FROM * WHERE (name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_1.Air Temperature' OR name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_2.Air Temperature') AND result < 30"

        # stop old container if it exists
        with hide('output', 'running'), settings(warn_only=True):
            local(f'docker rm -f {container_name} > /dev/null 2>&1 && echo "Removed container" || true', capture=True)

        # start new container
        with shell_env(STREAM_NAME=stream_name, SOURCE_SYSTEM=stream["SOURCE_SYSTEM"],
                       TARGET_SYSTEM=stream["TARGET_SYSTEM"], GOST_SERVER=stream["GOST_SERVER"],
                       KAFKA_BOOTSTRAP_SERVERS=stream["KAFKA_BOOTSTRAP_SERVERS"], FILTER_LOGIC=stream["FILTER_LOGIC"]):
            with hide('output', 'running'), settings(warn_only=True):
                return local('docker run '
                             '-dit '
                             '--network host '
                             '--restart always '
                             '-e "STREAM_NAME=$STREAM_NAME" '
                             '-e "SOURCE_SYSTEM=$SOURCE_SYSTEM" '
                             '-e "TARGET_SYSTEM=$TARGET_SYSTEM" '
                             '-e "KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP_SERVERS" '
                             '-e "GOST_SERVER=$GOST_SERVER" '
                             '-e "FILTER_LOGIC=$FILTER_LOGIC" '
                             '-e "LOG_LEVEL=DEBUG" '
                             f'--name {container_name} '
                             'iot4cps/streamengine '
                             '|| true', capture=True).stdout


@task(default=True)
def local_deploy_multi(system_uuid="0000", stream_name="test-stream", stream=None, logger=None):
    """
    Deploys a stream with the given parameters locally
    :param system_uuid: UUID of the system - unique RAMI 4.0 station
    :param stream_name: name of the stream app
    :param stream: attribute dictionary for stream with keys SOURCE_SYSTEM, TARGET_SYSTEM,
    KAFKA_BOOTSTRAP_SERVERS, GOST_SERVER, and FILTER_LOGIC
    :return:
    """
    # run('git clone https://git-service.ait.ac.at/im-IoT4CPS/WP5-lifecycle-mgmt.git /WP5-lifecycle-mgmt')
    import pdb
    # pdb.set_trace()
    with cd("."):
        # image name is 'iot4cps/streamapp', container_name is the container name
        with hide('output', 'running'), settings(warn_only=True):
            cur_frame = inspect.currentframe()
            s = f"(Re-)building Dockerfile named 'iot4cps/multi-source-stream'. "\
                f"Method was called from: {inspect.getouterframes(cur_frame, 2)[-1].filename}"\
                f" in the directory {os.path.realpath(os.path.curdir)}"
            if logger: logger.info(s)
            else: print(s)

            # Build the Dockerfile dependent of the caller's directory
            if inspect.getouterframes(cur_frame, 2)[-1].filename.endswith("views/StreamHandler/stream_tester.py"):
                local('docker build -t iot4cps/multi-source-stream ../../TimeSeriesJoiner')
            else:
                local('docker build -t iot4cps/multi-source-stream TimeSeriesJoiner')

        container_name = build_name(system_uuid, stream_name)
        if stream is None:  # fill with test values if emptystream = dict()
            print("WARNING, no parameter given.")
            stream = dict()
            stream["SOURCE_SYSTEM"] = "cz.icecars.iot4cps-wp5-CarFleet.Car1"
            stream["TARGET_SYSTEM"] = "cz.icecars.iot4cps-wp5-CarFleet.Car2"
            stream["KAFKA_BOOTSTRAP_SERVERS"] = "127.0.0.1:9092"
            stream["GOST_SERVER"] = "127.0.0.1:8082"
            stream["FILTER_LOGIC"] = None
        else:
            # execute the filter logic to load the variables and functions into the memory
            if stream.get("FILTER_LOGIC"):
                exec(stream.get("FILTER_LOGIC"))
                s = f"Loaded custom FILTER_LOGIC: {locals()['ADDITIONAL_ATTRIBUTES']}"

            else:
                s = f"No filter logic given, using default."
                stream["FILTER_LOGIC"] = ""
            if logger: logger.info(s)
            else: print(s)

        # stop old container if it exists
        with hide('output', 'running'), settings(warn_only=True):
            local(f'docker rm -f {container_name} > /dev/null 2>&1 && echo "Removed container" || true', capture=True)

        # start new container
        with shell_env(STREAM_NAME=stream_name, SOURCE_SYSTEM=stream["SOURCE_SYSTEM"],
                       TARGET_SYSTEM=stream["TARGET_SYSTEM"], GOST_SERVER=stream["GOST_SERVER"],
                       KAFKA_BOOTSTRAP_SERVERS=stream["KAFKA_BOOTSTRAP_SERVERS"], FILTER_LOGIC=stream["FILTER_LOGIC"]):
            # TODO pass the configs into the blueprint joiner
            with hide('output', 'running'), settings(warn_only=True):
                return local('docker run '
                             '-dit '
                             '--network host '
                             '--restart always '
                             '-e "STREAM_NAME=$STREAM_NAME" '
                             '-e "SOURCE_SYSTEM=$SOURCE_SYSTEM" '
                             '-e "TARGET_SYSTEM=$TARGET_SYSTEM" '
                             '-e "KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP_SERVERS" '
                             '-e "GOST_SERVER=$GOST_SERVER" '
                             '-e "FILTER_LOGIC=$FILTER_LOGIC" '
                             f'--name {container_name} '
                             'iot4cps/multi-source-stream '
                             '|| true', capture=True).stdout


@task
def local_down(system_uuid="0000", stream_name="test-stream"):
    """
    Stops the stream with the given parameters locally
    :param system_uuid: UUID of the system - unique RAMI 4.0 station
    :param stream_name: name of the stream app
    :return: The response of the docker rm -f command
    """
    # image name is 'iot4cps/streamapp', container_name is the container name, differing in their env vars
    container_name = build_name(system_uuid, stream_name)

    # stop container if it exists
    with hide('output', 'running'), settings(warn_only=True):
        return local(f'docker rm -f {container_name} > /dev/null 2>&1 && echo "Removed {container_name}" || '
                     f'echo "{container_name}" was not running.', capture=True).stdout


@task
def local_is_deployed(system_uuid="0000", stream_name="test-stream"):
    """
    Checks whether the stream with the given parameters already runs locally
    :param system_uuid: UUID of the system - unique RAMI 4.0 station
    :param stream_name: name of the stream app
    :return: True if it runs, else False
    """
    # image name is 'iot4cps/streamapp', container_name is the container name, differing in their env vars
    container_name = build_name(system_uuid, stream_name)
    with hide('output', 'running'), settings(warn_only=True):
        response = local("docker ps || true", capture=True).stdout
        if container_name in response:
            return True
        else:
            return False


@task
def local_get_all_streams():
    """
    Checks whether the stream with the given parameters already runs locally
    :return: True if it runs, else False
    """
    # image name is 'iot4cps/streamapp', container_name is the container name, differing in their env vars
    with hide('output', 'running'), settings(warn_only=True):
        response = local("docker ps --no-trunc || true", capture=True).stdout
        keys = response.splitlines()[0].split()
        return [{keys[i]: res for i, res in enumerate([res for res in line.split("  ") if res != ""])}
                for line in response.splitlines()[1:]]


@task
def local_logs(system_uuid="0000", stream_name="test-stream"):
    """
    Returns the logs of the locally deployed stream with the given parameters
    :param system_uuid: UUID of the system - unique RAMI 4.0 station
    :param stream_name: name of the stream app
    :return: None if it doesn't run, else the logs as string and following the logs if called in main.
    """
    container_name = build_name(system_uuid, stream_name)

    if not local_is_deployed(system_uuid, stream_name):
        print(f"Nothing to remove, no container called '{container_name}'.")
        return None

    # live log if module is called as main, else show only logs so far
    if __name__ == "__main__":
        local(f'docker logs -f {container_name} || true')
    else:
        with hide('output', 'running'), settings(warn_only=True):
            return local(f'docker logs {container_name} || true', capture=True).stdout


@task
def local_stats(system_uuid="0000", stream_name="test-stream"):
    """
    Returns statistics of the locally deployed stream with the given parameters
    :param system_uuid: UUID of the system - unique RAMI 4.0 station
    :param stream_name: name of the stream app
    :return: Statistics of the stream as dictionary
    """

    # image name is 'iot4cps/streamapp', container_name is the container name, differing in their env vars
    container_name = build_name(system_uuid, stream_name)

    # Return none if there the container is not running
    if not local_is_deployed(system_uuid, stream_name):
        return None

    # Fill a stats dictionary with relevant info
    # https://stackoverflow.com/questions/21443690/fabric-is-there-any-way-to-capture-run-stdout/35609598
    stats = dict()
    with hide('output', 'running'), settings(warn_only=True):
        stats["Running"] = local("docker inspect -f '{{.State.Running}}' " + container_name, capture=True).stdout
        stats["Restarting"] = local("docker inspect -f '{{.State.Restarting}}' " + container_name, capture=True).stdout
        stats["StartedAt"] = local("docker inspect -f '{{.State.StartedAt}}' " + container_name, capture=True).stdout
        stats["FinishedAt"] = local("docker inspect -f '{{.State.FinishedAt}}' " + container_name, capture=True).stdout
        stats["ExitCode"] = local("docker inspect -f '{{.State.ExitCode}}' " + container_name, capture=True).stdout
        # stats["Error"] = local("docker inspect -f '{{.State.Error}}' " + container_name, capture=True).stdout  # empty
        # stats[".Config.Env"] = local("docker inspect -f '{{.Config.Env}}' " + container_name, capture=True).stdout
        stats[".Config.Image"] = local("docker inspect -f '{{.Config.Image}}' " + container_name, capture=True).stdout
        stats[".NetworkSettings.Gateway"] = local("docker inspect -f '{{.NetworkSettings.Gateway}}' " + container_name,
                                                  capture=True).stdout

    return stats


def build_name(system_uuid="0000", stream_name="test-stream"):
    return f"StreamApp_{system_uuid}_{stream_name}"
