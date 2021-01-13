import aiohttp
from functools import reduce

import requests
import math
from .provider import Provider

BASE_URL = "http://neuromorpho.org/api"


def filter_values(values, allowed_values=[], not_allowed_values=[], exact=True):
    return list(filter(lambda value: (
            reduce(lambda a, b: (a and b), [allowed in list(map(lambda x: x.strip().lower(), value.split(','))) for allowed in allowed_values] if exact else [allowed in value for allowed in allowed_values], True) and
            reduce(lambda a, b: (a and b), [not_allowed not in list(map(lambda x: x.strip().lower(), value.split(','))) for not_allowed in not_allowed_values] if exact else [not_allowed not in value for not_allowed in not_allowed_values], True)
    ), values))


class NeuroMorphoProvider(Provider):
    def __init__(self):
        super(NeuroMorphoProvider, self).__init__()
        self.source = 'Neuro Morpho'

    async def get_all_field_value(self, field_name):
        num_page = 0
        size = 100
        fetched = False
        total_pages = 1
        all_values = []
        while num_page <= (total_pages - 1) or fetched is False:
            url = f"{BASE_URL}/neuron/fields/{field_name}?page={num_page}&size={size}"
            print(f'Fetch url {url}')
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, allow_redirects=True, timeout=30) as response:
                        print(f'Response status for url {url} {response.status}')
                        if response is not None and response.status == 200:
                            data = await response.json()
                            all_values.extend(data['fields'])
            except Exception as ex:
                print(f"Exception retrieving field values {ex}")
            num_page = num_page + 1
            fetched = True
        return all_values

    async def search(self, start=0, hits_per_page=50):
        num_page = math.floor(start / hits_per_page)
        size = hits_per_page
        domain_allowed_values = filter_values(await self.get_all_field_value('domain'), ['dendrites', 'soma', 'axon'])
        original_format_allowed_values = filter_values(await self.get_all_field_value('original_format'), ['.asc'], exact=False)
        attributes_allowed_values = filter_values(await self.get_all_field_value('attributes'), ['diameter', '3d', 'angles'])
        physical_integrity_values = filter_values(await self.get_all_field_value('Physical_Integrity'), ['dendrites complete'], ['no axon'])
        print(f"Domains {domain_allowed_values}")
        print(f"Original format {original_format_allowed_values}")
        print(f"Attributes {attributes_allowed_values}")
        print(f"Physical Integrity {physical_integrity_values}")
        params = {
            'brain_region': ['hippocampus'],
            'domain': domain_allowed_values,
            'original_format': original_format_allowed_values,
            'attributes': attributes_allowed_values,
            'Physical_Integrity': physical_integrity_values
        }
        try:
            fetched = False
            total_pages = 1
            all_items = []
            while num_page <= (total_pages - 1) or fetched is False:
                url = f"{BASE_URL}/neuron/select?page={num_page}&size={size}"
                print(f'Fetch url {url}')
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=params, allow_redirects=True, timeout=30) as response:
                            print(f'Response status for url {url} {response.status}')
                            if response is not None and response.status == 200:
                                data = await response.json()
                                items = self.map_datasets(data['_embedded']['neuronResources'])
                                all_items.extend(items)
                                total_pages = data['page']['totalPages']
                except Exception as ex:
                    print(f"exception retrieving values {ex}")
                num_page = num_page + 1
                fetched = True
            return all_items
        except Exception as ex:
            raise ex

    def map_datasets(self, datasets=[]):
        try:
            mapped_datasets = [self.__map_dataset__(x) for x in datasets]
            return mapped_datasets
        except Exception as ex:
            print(f"Exception on map datasets {ex}")
            raise ex

    def __map_dataset__(self, dataset):
        regions = dataset['brain_region']
        cell_types = dataset['cell_type']
        brain_region = ''
        secondary_region = ''
        primary_cell_type = ''
        secondary_cell_type = ''
        if len(regions) > 0:
            brain_region = regions[0]
        if len(regions) > 1:
            secondary_region = regions[1]

        if len(cell_types) > 0:
            primary_cell_type = cell_types[0]
        if len(cell_types) > 1:
            secondary_cell_type = cell_types[1]

        original_format_ext = dataset['original_format'].split('.')[-1]

        try:
            return {
                'id': dataset['neuron_id'],
                'name': dataset['neuron_name'],
                'description': dataset['note'],
                'archive': dataset['archive'],
                'region': brain_region,
                'secondary_region': secondary_region,
                'cell_type': primary_cell_type,
                'secondary_cell_type': secondary_cell_type,
                'species': dataset['species'],
                'icon': dataset['png_url'],
                'link': dataset['_links']['self']['href'],
                'original_format': dataset['original_format'],
                'download_original_format': f"http://neuromorpho.org/dableFiles/{dataset['archive'].lower()}/Source-Version/{dataset['neuron_name']}.{original_format_ext}",
                'page_link': f"http://neuromorpho.org/neuron_info.jsp?neuron_name={dataset['neuron_name']}",
                'protocol': dataset['protocol'],
                'morphologies': dataset['attributes'],
                'structural_domains': dataset['domain'],
                'source': self.source
            }
        except Exception as ex:
            raise ex
