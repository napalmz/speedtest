#!/usr/bin/env python3

import configparser, os, sys, argparse, json, time, subprocess

from influxdb_client                   import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError
from influxdb_client.client.write_api  import SYNCHRONOUS

class configManager():

    def __init__(self, config):
        #print('Loading Configuration File {}'.format(config))
        #self.test_server = []
        #config_file = os.path.join(os.getcwd(), config)
        #if os.path.isfile(config_file):
        #    self.config = configparser.ConfigParser()
        #    self.config.read(config_file)
        #else:
        #    print('ERROR: Unable To Load Config File: {}'.format(config_file))
        #    sys.exit(1)
        #self._load_config_values()

        print('Loading Configuration Enviroments')
        self._load_env_values()
        print('Configuration Successfully Loaded')

    def _load_config_values(self):

        # General
        self.delay  = self.config['GENERAL'].getint('Delay', fallback=2)
        self.output = self.config['GENERAL'].getboolean('Output', fallback=True)

        # Influxdb2
        self.influx_url    = self.config['INFLUXDB'].get('Url', fallback='http://localhost:8086')
        self.influx_token  = self.config['INFLUXDB'].get('Token', fallback='')
        self.influx_org    = self.config['INFLUXDB'].get('Org', fallback='')
        self.influx_bucket = self.config['INFLUXDB'].get('Bucket', fallback='')

        # Speedtest
        test_server = self.config['SPEEDTEST'].get('Server', fallback=None)
        if test_server:
            self.test_server.append(test_server)

    def _load_env_values(self):

        # General
        self.delay  = int(os.environ.get('GENERAL_DELAY', 2))
        self.output = os.environ.get('GENERAL_OUTPUT', True)

        # Influxdb2
        self.influx_url    = os.environ.get('INFLUX_URL', 'http://localhost:8086')
        self.influx_token  = os.environ.get('INFLUX_TOKEN', 'my-token')
        self.influx_org    = os.environ.get('INFLUX_ORG', 'my-org')
        self.influx_bucket = os.environ.get('INFLUX_BUCKET', 'my-bucket')

        # Speedtest
        test_server = os.environ.get('SPEEDTEST_SERVER')
        if test_server:
            self.test_server.append(test_server)


class InfluxdbSpeedtest():

    def __init__(self, config=None):

        self.config = configManager(config=config)
        self.output = self.config.output
        # Init version 2.X
        self.influx_client = InfluxDBClient(
            url=self.config.influx_url,
            token=self.config.influx_token,
            org=self.config.influx_org
        )

        self.speedtest = None
        self.results = None
        self.speed_result = None

    def send_results(self):

        speed_result = subprocess.check_output(['SpeedTest', '--output', 'json']).decode(sys.stdout.encoding).strip()
        result_dict = json.loads(speed_result)

        input_points = [
            {
                'measurement': 'speed_test_results',
                'fields': {
                    'download': float(result_dict['download']),
                    'upload': float(result_dict['upload']),
                    'ping': float(result_dict['ping']) #['server']['latency']
                },
                'tags': {
                    'server': result_dict['server']['sponsor']
                }
            }
        ]

        if self.output:
            print('Download: {}'.format(str(result_dict['download'])))
            print('Upload: {}'.format(str(result_dict['upload'])))

        self.write_influx_data(input_points)

    def run(self):

        while True:

            self.send_results()

            time.sleep(self.config.delay)

    def write_influx_data(self, json_data):
        """
        Writes the provided JSON to the database
        :param json_data:
        :return:
        """
        if self.output:
            print(json_data)

        try:
            self.influx_client.write_api(write_options=SYNCHRONOUS).write(bucket=self.config.influx_bucket, record=json_data)
        except InfluxDBError as e:
            if hasattr(e, 'code') and e.code == 404:

                print('Database {} Does Not Exist.  Attempting To Create'.format(self.config.influx_database))

                # TODO Grab exception here
                self.influx_client.buckets_api().create_bucket(bucket=self.config.influx_bucket, org=self.config.influx_org)
                self.influx_client.write_api(write_options=SYNCHRONOUS).write(bucket=self.config.influx_bucket, record=json_data)
    
                return

            print('ERROR: Failed To Write To InfluxDB')
            print(e)

        if self.output:
            print('Written To Influx: {}'.format(json_data))


def main():

    parser = argparse.ArgumentParser(description="A tool to send Speedtest statistics to InfluxDB")
    parser.add_argument('--config', default='config.ini', dest='config', help='Specify a custom location for the config file')
    args = parser.parse_args()
    collector = InfluxdbSpeedtest(config=args.config)
    collector.run()


if __name__ == '__main__':
    main()
