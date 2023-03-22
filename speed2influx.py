#!/usr/bin/env python3

import configparser, os, sys, argparse, json, time, subprocess
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
#import speedtest

class configManager():

    def __init__(self, config):
        print('Loading Configuration File {}'.format(config))
        self.test_server = []
        config_file = os.path.join(os.getcwd(), config)
        if os.path.isfile(config_file):
            self.config = configparser.ConfigParser()
            self.config.read(config_file)
        else:
            print('ERROR: Unable To Load Config File: {}'.format(config_file))
            sys.exit(1)

        self._load_config_values()
        print('Configuration Successfully Loaded')

    def _load_config_values(self):

        # General
        self.delay = self.config['GENERAL'].getint('Delay', fallback=2)
        self.output = self.config['GENERAL'].getboolean('Output', fallback=True)

        # InfluxDB
        self.influx_address = self.config['INFLUXDB']['Address']
        self.influx_port = self.config['INFLUXDB'].getint('Port', fallback=8086)
        self.influx_database = self.config['INFLUXDB'].get('Database', fallback='speedtests')
        self.influx_user = self.config['INFLUXDB'].get('Username', fallback='')
        self.influx_password = self.config['INFLUXDB'].get('Password', fallback='')
        self.influx_ssl = self.config['INFLUXDB'].getboolean('SSL', fallback=False)
        self.influx_verify_ssl = self.config['INFLUXDB'].getboolean('Verify_SSL', fallback=True)

        # Speedtest
        test_server = self.config['SPEEDTEST'].get('Server', fallback=None)
        if test_server:
            self.test_server.append(test_server)


class InfluxdbSpeedtest():

    def __init__(self, config=None):

        self.config = configManager(config=config)
        self.output = self.config.output
        self.influx_client = InfluxDBClient(
            self.config.influx_address,
            self.config.influx_port,
            username=self.config.influx_user,
            password=self.config.influx_password,
            database=self.config.influx_database,
            ssl=self.config.influx_ssl,
            verify_ssl=self.config.influx_verify_ssl
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
            self.influx_client.write_points(json_data)
        except (InfluxDBClientError, ConnectionError, InfluxDBServerError) as e:
            if hasattr(e, 'code') and e.code == 404:

                print('Database {} Does Not Exist.  Attempting To Create'.format(self.config.influx_database))

                # TODO Grab exception here
                self.influx_client.create_database(self.config.influx_database)
                self.influx_client.write_points(json_data)

                return

            print('ERROR: Failed To Write To InfluxDB')
            print(e)

        if self.output:
            print('Written To Influx: {}'.format(json_data))


def main():

    parser = argparse.ArgumentParser(description="A tool to send Plex statistics to InfluxDB")
    parser.add_argument('--config', default='config.ini', dest='config', help='Specify a custom location for the config file')
    args = parser.parse_args()
    collector = InfluxdbSpeedtest(config=args.config)
    collector.run()


if __name__ == '__main__':
    main()
