from typing import Dict, List, Union
import json
import requests
from trellojira.model import TrelloList, TrelloCard


class TrelloAPIError(Exception):
    def __init__(self, r=None, text=None, js=None):
        super().__init__(text)


# TODO Exception texts
class TrelloAPI(object):

    # noinspection SpellCheckingInspection
    CUSTOM_FIELDS_PLUGIN_ID = "56d5e249a98895a9797bebb9"

    def __init__(self, key, token, board_id, jira_custom_field_code):
        self.key = key
        self.token = token
        self.board_id = board_id
        self.jira_custom_field_code = jira_custom_field_code

        self.map_api_id_list = self._load_lists()  # type: Dict[str, TrelloList]
        self.map_api_id_card = {}  # type: Dict[str, TrelloCard]

    def get_json(self, url: str, params: Dict[str, str], bad_code_text=None) -> Union[List, Dict]:
        new_params = {
            "key": self.key,
            "token": self.token
        }
        new_params.update(params)

        r = requests.get(url, params=new_params)
        if r.status_code != 200:
            raise TrelloAPIError(r, text=bad_code_text)

        return r.json()

    def _load_lists(self) -> Dict[str, TrelloList]:
        resp_json = self.get_json("https://api.trello.com/1/boards/{}/lists/".format(self.board_id), {"fields": "name"})

        try:
            return {j["id"]: TrelloList(api_id=j["id"], name=j["name"]) for j in resp_json}
        except KeyError as e:
            raise TrelloAPIError(text="No key in API response", js=resp_json) from e

    # TODO Finish
    @staticmethod
    def _preprocess_jira_link(raw_link: str) -> str:
        return raw_link

    def load_cards(self) -> List[TrelloCard]:
        url = "https://api.trello.com/1/boards/{}/cards/open/".format(self.board_id)
        params = {
            "fields": "name,idList"
        }

        resp_json = self.get_json(url, params)

        for j in resp_json:
            try:
                trello_list = self.map_api_id_list.get(j["idList"])
                if trello_list is None:
                    raise TrelloAPIError("List ID {} not loaded".format(j["idList"]), js=j)

                self.map_api_id_card[j["id"]] = TrelloCard(
                    name=j["name"],
                    api_id=j["id"],
                    trello_list=trello_list
                )
            except KeyError as e:
                raise TrelloAPIError(text="No key in API response", js=j) from e

        # Fetching custom fields

        batch_url = "https://api.trello.com/1/batch/"
        card_ids = [c.api_id for c in self.map_api_id_card.values()]
        chunk_size = 10

        def card_id_chunks():
            for i in range(0, len(card_ids), chunk_size):
                yield card_ids[i:i+chunk_size]

        resp_json_total = []

        for card_id_chunk in card_id_chunks():
            batch_params = {
                "urls": ",".join(["/cards/{}/pluginData/".format(cid) for cid in card_id_chunk])
            }
            resp_json = self.get_json(batch_url, batch_params)
            # Checking for response count
            if len(resp_json) != len(card_id_chunk):
                raise TrelloAPIError(
                    text="Length of result of batch does not match number of requested cards ({})".format(
                        ",".join(card_ids)
                    ),
                    js=resp_json
                )
            # Appending to all results
            resp_json_total.extend(resp_json)

        # Parsing custom fields data

        for idx, card_id in enumerate(card_ids):
            batch_part_resp = resp_json_total[idx]

            # Checking part of batch status
            if "200" not in batch_part_resp:
                raise TrelloAPIError(
                    text="Bad status code for plugin data request for card {}".format(card_id),
                    js=batch_part_resp
                )

            # Filtering data for Custom Fields plugin
            plugin_data_list = batch_part_resp["200"]
            cf_plugin_data_list = [pd for pd in plugin_data_list if pd.get("idPlugin") == self.CUSTOM_FIELDS_PLUGIN_ID]

            # Checking for abnormal count of plugin data
            if len(cf_plugin_data_list) == 0:
                continue
            elif len(cf_plugin_data_list) != 1:
                raise TrelloAPIError("More than one data for Custom Fields plugin.", js=plugin_data_list)
            # Getting plugin data
            cf_plugin_data = cf_plugin_data_list[0]

            # Checking if card ID matches model ID in plugin data
            if cf_plugin_data.get("idModel") != card_id:
                raise TrelloAPIError("Card ID {} mismatch for plugin data.".format(card_id), js=plugin_data_list)

            cf_dict = json.loads(cf_plugin_data.get("value"))
            self.map_api_id_card[card_id].jira_key = self._preprocess_jira_link(
                cf_dict["fields"].get(self.jira_custom_field_code)
            )

        return list(self.map_api_id_card.values())
