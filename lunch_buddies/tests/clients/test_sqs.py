import datetime
import json
import uuid

import lunch_buddies.clients.sqs as module


def test_json_round_trip_encoding():
    input_object = [uuid.uuid4(), datetime.datetime.now()]

    output_object = json.loads(
        json.dumps(
            input_object,
            cls=module.RoundTripEncoder,  
        ),
        cls=module.RoundTripDecoder,
    )

    assert input_object == output_object
