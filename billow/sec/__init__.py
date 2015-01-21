"""
billow Security API
"""
import billow


class sec():

    def __init__(self, region):
        self.region = region
        self.account_id = None

    def get_account_id(self):
        if not self.account_id:
            iam = boto.connect_iam()
            self.account_id = iam.get_user()['get_user_response']['get_user_result'][
                'user']['arn'].split(':')[4]
        return self.account_id
