
class TrelloList(object):
    def __init__(self, name: str, api_id: str):
        self.name = name
        self.api_id = api_id

    def __str__(self):
        return "<TrelloList: {}>".format(self.name)


class TrelloCard(object):
    def __init__(self, name: str, api_id: str, trello_list: TrelloList=None, jira_key: str=None):
        pass
        self.name = name
        self.api_id = api_id
        self.trello_list = trello_list
        self.jira_key = jira_key

    def __str__(self):
        return "<TrelloCard: {}{}{}>".format(
            self.name,
            "({})".format(self.jira_key) if self.jira_key else "",
            " ({})".format(self.trello_list.name) if self.trello_list else ""
        )
