import argparse
import requests
import json
import os
import logging

def analyze_file(file_path, endpoint_url, api_key=None):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = f.read()
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    payload = {'content': data, 'filename': os.path.basename(file_path)}
    response = requests.post(endpoint_url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()
    return response.json()

def send_to_dashboard(report, dashboard_url, dashboard_api_key=None):
    headers = {'Content-Type': 'application/json'}
    if dashboard_api_key:
        headers['Authorization'] = f'Bearer {dashboard_api_key}'
    response = requests.post(dashboard_url, headers=headers, data=json.dumps(report))
    response.raise_for_status()
    return response.json()

def main():
    parser = argparse.ArgumentParser(description='Security Auditor CLI')
    parser.add_argument('file', help='Path to the file to analyze')
    parser.add_argument('--endpoint', required=True, help='AI model endpoint URL')
    parser.add_argument('--api-key', help='API key for the model endpoint')
    parser.add_argument('--dashboard', help='Dashboard URL for reporting')
    parser.add_argument('--dashboard-key', help='API key for the dashboard')
    parser.add_argument('--log', default='audit.log', help='Log file path')
    args = parser.parse_args()

    logging.basicConfig(filename=args.log, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        logging.info(f'Analyzing file: {args.file}')
        result = analyze_file(args.file, args.endpoint, args.api_key)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        logging.info('Analysis result: %s', json.dumps(result))
        if args.dashboard:
            dashboard_result = send_to_dashboard(result, args.dashboard, args.dashboard_key)
            print('Dashboard response:', dashboard_result)
            logging.info('Dashboard response: %s', json.dumps(dashboard_result))
    except Exception as e:
        logging.error('Error: %s', str(e))
        print('Error:', e)

if __name__ == '__main__':
    main()
