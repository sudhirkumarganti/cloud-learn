def lambda_handler(event, context):
    return {
        "message": "Hello from Lambda",
        "function_name": "hello-lambda",
        "received_event": event,
    }