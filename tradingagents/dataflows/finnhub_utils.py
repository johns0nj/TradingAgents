import json
import os
import re
from dotenv import load_dotenv

load_dotenv()  # 加载.env文件

def clean_text(text):
    """清理文本中的特殊字符，避免编码问题"""
    if not isinstance(text, str):
        return str(text)
    # 移除零宽空格和其他特殊字符
    text = re.sub(r'[\u200b\u200c\u200d\u2060\u2061\u2062\u2063\u2064]', '', text)
    # 移除其他可能导致编码问题的字符
    text = text.encode('utf-8', errors='ignore').decode('utf-8')
    return text

# 测试是否成功读取API Key
#print("FINNHUB_API_KEY:", os.getenv("FINNHUB_API_KEY"))

def get_data_in_range(ticker, start_date, end_date, data_type, data_dir, period=None):
    """
    Gets finnhub data saved and processed on disk.
    Args:
        start_date (str): Start date in YYYY-MM-DD format.
        end_date (str): End date in YYYY-MM-DD format.
        data_type (str): Type of data from finnhub to fetch. Can be insider_trans, SEC_filings, news_data, insider_senti, or fin_as_reported.
        data_dir (str): Directory where the data is saved.
        period (str): Default to none, if there is a period specified, should be annual or quarterly.
    """

    if period:
        data_path = os.path.join(
            data_dir,
            "finnhub_data",
            data_type,
            f"{ticker}_{period}_data_formatted.json",
        )
    else:
        data_path = os.path.join(
            data_dir, "finnhub_data", data_type, f"{ticker}_data_formatted.json"
        )

    data = open(data_path, "r")
    data = json.load(data)

    # filter keys (date, str in format YYYY-MM-DD) by the date range (str, str in format YYYY-MM-DD)
    filtered_data = {}
    for key, value in data.items():
        if start_date <= key <= end_date and len(value) > 0:
            filtered_data[key] = value
    return filtered_data
