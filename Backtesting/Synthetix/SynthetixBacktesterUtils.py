from enum import Enum
import json
import os
from GlobalUtils.logger import *
from web3 import *
from web3.datastructures import AttributeDict
from hexbytes import HexBytes

from dotenv import load_dotenv

load_dotenv()

provider_url = os.getenv('BASE_PROVIDER_RPC')
client = Web3(Web3.HTTPProvider(provider_url))

MULTICALL_GAS = 500000

class ContractAddresses(Enum):
    PERPS = Web3.to_checksum_address('0x0a2af931effd34b81ebcc57e3d3c9b1e1de1c9ce')

def get_perps_contract():
        try:
            json_filepath = 'Backtesting/Synthetix/perps_contract_abi.json'
            with open(json_filepath, 'r') as file:
                abi = json.load(file)
        
        except FileNotFoundError:
            logger.error(f"SynthetixBacktester - Contract ABI file does not exist at filepath: {json_filepath}")
            raise
        except json.JSONDecodeError:
            logger.error("SynthetixBacktester - ABI file is not valid JSON")
            raise
        return client.eth.contract(address=ContractAddresses.PERPS.value, abi=abi)

def parse_event_data(events):
    try:
        parsed_events = []
        for event in events:
            market_id = event['args']['marketId']
            price = event['args']['price'] / 10**18
            size = event['args']['size'] / 10**18
            skew = event['args']['skew'] / 10**18
            funding_rate = (event['args']['currentFundingRate'] / 10**18) / 3
            funding_velocity = event['args']['currentFundingVelocity'] / 10**18

            data = {
                "market_id": market_id,
                "price": price,
                "size": size,
                "skew": skew,
                "funding_rate": funding_rate,
                "funding_velocity": funding_velocity,
                "block_number": event['blockNumber']
            }
            logger.info(f'parsed event data = {data}')
            parsed_events.append(data)

        return parsed_events

    except Exception as e:
        logger.error(f'Error parsing event data: {e}')

def _convert_to_dict(data):
    """
    Recursively converts data which may include nested AttributeDicts and HexBytes into standard dictionaries.
    """
    if isinstance(data, AttributeDict) or isinstance(data, dict):
        return {key: _convert_to_dict(value) for key, value in dict(data).items()}
    elif isinstance(data, HexBytes):
        return data.hex()
    elif isinstance(data, list):
        return [_convert_to_dict(item) for item in data]
    else:
        return data

def save_events_to_json(events, filename='event_logs.json'):
    """
    Appends a list of event data to a JSON file. If the file doesn't exist, it creates a new one.
    """
    events_dict = [_convert_to_dict(event) for event in events]
    
    try:
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            with open(filename, 'r') as file:
                existing_data = json.load(file)
                existing_data.extend(events_dict)
        else:
            existing_data = events_dict

        with open(filename, 'w') as file:
            json.dump(existing_data, file, indent=4)
        print(f"Data successfully appended to {filename}")

    except TypeError as e:
        print(f"Failed to append data to {filename}: {str(e)}")
    except IOError as e:
        print(f"Failed to open {filename} for appending: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filename}: {str(e)}")

def preprocess_rates(rates):
    preprocessed_rates = {}
    for rate in rates:
        block_number = rate['block_number']
        preprocessed_rates[block_number] = rate
    return sorted(preprocessed_rates.values(), key=lambda x: x['block_number'])
