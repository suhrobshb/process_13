from twilio.rest import Client

class CallHandler:
    """
    Automate voice calls via Twilio or similar API.
    """

    def __init__(self, account_sid: str, auth_token: str):
        self.client = Client(account_sid, auth_token)

    def make_call(self, to_number: str, from_number: str, twiml_url: str):
        """
        Place a call and play instructions from a TwiML URL.
        """
        call = self.client.calls.create(
            to=to_number,
            from_=from_number,
            url=twiml_url
        )
        return call.sid
