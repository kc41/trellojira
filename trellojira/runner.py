from sys import exit
from trellojira.api import TrelloAPI


def main():
    try:
        # noinspection PyUnresolvedReferences
        from trellojira.local_settings import trello_key, trello_token, board_id, jira_custom_field_code
    except ImportError:
        print("No local settings found!")
        exit(-1)
        return  # For static analyzer
    api = TrelloAPI(trello_key, trello_token, board_id, jira_custom_field_code)
    trello_cards = api.load_cards()
    print([str(tc) for tc in trello_cards])


if __name__ == '__main__':
    main()
