import requests

url = "http://127.0.0.1:8089/todos"
headers = {
    "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTA3NDk1NzIsInN1YiI6ImFAYS5jb20iLCJpYXQiOjE3NTA2NjMxNzIsImV4dHJhcyI6e319.FmYJTeEEEuGnlactFY2YexRg3PHvXjRzc_3p1EOHxIw",
    "Accept": "*/*",
    "Host": "127.0.0.1:8089",
    "Connection": "keep-alive",
    # 'Cookie': 'token="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTA3NDk1NzIsInN1YiI6ImFAYS5jb20iLCJpYXQiOjE3NTA2NjMxNzIsImV4dHJhcyI6e319.FmYJTeEEEuGnlactFY2YexRg3PHvXjRzc_3p1EOHxIw"'
}
response = requests.get(url, headers=headers)
data = response.content
