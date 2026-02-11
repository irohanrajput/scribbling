import logging
import requests


def process_order(order_id):
    logging.info("processing order")
    response = requests.get("https://example.com")
    return response.text


def refund_order(order_id):
    try:
        data = open("refund.txt").read()
    except Exception as e:
        logging.error(e)
