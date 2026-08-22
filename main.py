# -*- coding: utf-8 -*-

# “2026南京工业大学安全知识考试”一键完成脚本
# Scwizard/HAM:BA4TLH
# 2025/08/14 (Rebuild at 2026/08/14)

# 交互流程:
#   1. 选择模式: 1=只做题(在线学习)  2=只做考试(正式考试)  3=都做
#   2. 正式考试目标分数(0-100)   [仅模式 2/3 询问]
#   3. 正式考试用时(分钟)        [仅模式 2/3 询问]
import json
import os
import random
import re
import sqlite3
import time
import secrets
import requests

# 登录后拿会话 id, 失效后请更新(登录后从浏览器 Cookie 里复制 PHPSESSID)
# PHPSESSID = str(input("请输入PHPSESSID:").strip())
# 上述方法不够简单，已经弃用，直接运行就行了

BASE_URL = "https://bwcks.njtech.edu.cn"
EXAM_URL = BASE_URL + "/Home/Zxks/index?ksmk={ksmk}&aa=bb"
ANSWER_URL = BASE_URL + "/Home/Question/addUserAnswers"

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = "database.db"

# 练习章节的ksmk
EXAM_CHAPTERS = ["10202", "10203", "10204", "10205", "10206"]
# 正式考试的ksmk
FINAL_EXAM = "10207"

UA = ("Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/151.0.0.0 Mobile Safari/537.36")

REQUEST_DELAY = 0.3  # 每次请求之间的间隔(秒)


def load_answers():
    """从数据库读取全部答案: {qId: option}."""
    conn = sqlite3.connect(DB_PATH)
    ans = {str(r[0]): r[1] for r in conn.execute("SELECT qId, option FROM tiku")}
    conn.close()
    return ans


def gen_phpsessid(length=32, alphanumeric=True) -> str:
    """
    生成一个随机的phpsessid
    """
    if alphanumeric:
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        return ''.join(secrets.choice(chars) for _ in range(length))
    return secrets.token_hex(length // 2)

def get_captcha(phpsessid):
    cookies = {
        'PHPSESSID': phpsessid,
    }

    headers = {
        'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'accept-language': 'zh-CN,zh;q=0.9',
        'priority': 'u=2, i',
        'referer': 'https://bwcks.njtech.edu.cn/Home/Index/logout',
        'sec-ch-ua': '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'image',
        'sec-fetch-mode': 'no-cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
        # 'cookie': 'PHPSESSID=mngmlldl01ig47898i81g2cbl5',
    }

    response = requests.get('https://bwcks.njtech.edu.cn/home/index/getverifycode.html', cookies=cookies, headers=headers)
    with open("captcha.png","wb") as f:
        f.write(response.content)
    try:
        os.startfile("captcha.png")
        return True
    except FileNotFoundError as e:
        print(f"尝试打开失败，请手动在文件夹中打开captcha，错误：{e}")
        os.startfile(os.getcwd())
        return False


# def ocrCaptcha():
#     ocr = ddddocr.DdddOcr(show_ad=False)
#     ocr.set_ranges("0123456789")
#     with open('captcha.png', 'rb') as f:
#         image = f.read()
#         res = ocr.classification(image)
#         return res

def make_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Origin": BASE_URL,
        "X-Requested-With": "XMLHttpRequest",
    })
    s.cookies.set("PHPSESSID", PHPSESSID)
    return s

def login(phpsessid, account, password, captcha):
    cookies = {
        'PHPSESSID': phpsessid,
    }

    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'zh-CN,zh;q=0.9',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://bwcks.njtech.edu.cn',
        'priority': 'u=1, i',
        'referer': 'https://bwcks.njtech.edu.cn/Home/Index/logout',
        'sec-ch-ua': '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }

    data = f'username={account}&password={password}&yzm={captcha}'

    response = requests.post('https://bwcks.njtech.edu.cn/Home/Index/login', cookies=cookies, headers=headers, data=data)
    return response

def parse_questions(text):
    """从 HTML 文本中解析 `var questions = [[...]][0]`, 返回题目列表."""
    if "var questions" not in text:
        raise RuntimeError("页面异常: 未找到 var questions, 请检查 PHPSESSID")
    for line in text.splitlines():
        if "var questions" in line:
            raw = line.split("var questions = ", 1)[1].strip().rstrip(";")
            if raw.endswith("[0]"):
                raw = raw[:-3]
            return json.loads(raw)[0]
    raise RuntimeError("未找到 var questions")


def fetch_exam(session, ksmk):
    """抓取考试页面, 返回 (ksmk, paper_id, questions)."""
    url = EXAM_URL.format(ksmk=ksmk)
    session.headers["Referer"] = url
    r = session.get(url, timeout=30)
    if "var ksmk" not in r.text:
        raise RuntimeError(f"页面异常: ksmk={ksmk}, 请检查 PHPSESSID 是否填写正确")
    km = re.search(r"var ksmk = '(\d+)';", r.text).group(1)
    pid = re.search(r"var paper_id = '(\d+)';", r.text).group(1)
    return km, pid, parse_questions(r.text)


def make_wrong_option(q, correct):
    """给出一道题的错误选项 id(用于自定义分数时故意答错)."""
    qtype = str(q.get("type", "1"))
    opts = q.get("optAry", [])
    if qtype == "2":  # 多选
        correct_ids = set(correct.split(","))
        for o in opts:
            if str(o["id"]) not in correct_ids:
                return str(o["id"])
        # 所有选项都是正确选项 -> 只选第一个(不完整, 应该会判错吧)
        return str(opts[0]["id"]) if opts else ""
    # 单选和判断
    for o in opts:
        if str(o["id"]) != correct:
            return str(o["id"])
    return ""


def pick_wrong_qids(questions, score):
    """根据目标分数, 随机搓个题"""
    n = len(questions)
    if n == 0:
        return set(), 0
    right = int(round(score * n / 100.0))
    right = max(0, min(n, right))
    wrong = n - right
    qids = [str(q["id"]) for q in questions]
    random.shuffle(qids)
    return set(qids[:wrong]), right


def submit(session, ksmk, paper_id, questions, answers, submit_type, wrong_qids=None):
    """构建并提交答案, 返回 (响应json, 题库缺失题号列表)."""
    wrong_qids = wrong_qids or set()
    qmap = {str(q["id"]): q for q in questions}
    ids = [str(q["id"]) for q in questions]
    missing = [i for i in ids if i not in answers]

    data = []
    for i in ids:
        if i in wrong_qids:
            opt = make_wrong_option(qmap[i], answers.get(i, ""))
        else:
            opt = answers.get(i, "")
        data.append({"id": i, "option": opt})

    r = session.post(ANSWER_URL, data={
        "qIdAry": json.dumps(ids),
        "type": submit_type,
        "paper_id": paper_id,
        "ksmk": ksmk,
        "data": json.dumps(data),
    }, timeout=30)
    return r.json(), missing


def print_result(tag, ksmk, questions, result, missing):
    info = result.get("info", {})
    ok = "success" if result.get("success") else "failed"
    print("[%s] ksmk=%s 题目=%d 正确率=%s 得分=%s [%s]" % (
        tag, ksmk, len(questions), info.get("rightPercent"),
        info.get("score"), ok))
    if missing:
        print("  warn: 题库缺少答案的题号: %s" % ",".join(missing))


def do_online_exams(session, answers):
    """只做题: 在线学习 10202-10206 满分完成."""
    for ksmk in EXAM_CHAPTERS:
        km, pid, questions = fetch_exam(session, ksmk)
        result, missing = submit(session, km, pid, questions, answers, "2")
        print_result("在线学习", km, questions, result, missing)
        time.sleep(REQUEST_DELAY)


def do_final_exam(session, answers, score, duration):
    """只做考试: 正式考试 10207, 自定义分数和时长."""
    km, pid, questions = fetch_exam(session, FINAL_EXAM)
    wrong_qids, right = pick_wrong_qids(questions, score)
    wait = max(0, duration) * 60
    print("[正式考试] ksmk=%s 题目=%d 目标分数=%s 预计答对=%d 答错=%d" % (
        km, len(questions), score, right, len(wrong_qids)))
    if wait > 0:
        print("等待 %d 秒(%.1f 分钟)后交卷..." % (wait, duration))
        time.sleep(wait)
    result, missing = submit(session, km, pid, questions, answers, "2", wrong_qids)
    print_result("正式考试", km, questions, result, missing)

def end():
    input("程序因为异常而结束运行.")
    exit()


if __name__ == "__main__":
    global PHPSESSID
    PHPSESSID = gen_phpsessid()
    print(f"生成一个随机的PHPSESSID: {PHPSESSID}")
    print("开始登录流程...")
    account = str(input("请输入账号：").strip())
    password = str(input("请输入密码：").strip())
    print("开始处决验证码...")
    while True:
        get_captcha(PHPSESSID)
        captcha = input("请输入你看到的验证码: ").strip()
        res = login(PHPSESSID, account, password, captcha)
        resJson = json.loads(res.text)
        if resJson['success'] == True:
            print("登录成功，开始刷课")
            break
        elif resJson['errorMsg'] == "验证码错误!":
            print("登陆失败：验证码错误，请重新输入")
            continue
        elif resJson['errorMsg'] == "用户名/密码不正确!":
            print("用户名/密码不正确!")
            end()
        else:
            print(f"未知异常：{resJson['errorMsg']}")
            end()

    answers = load_answers()
    print("题库共 %d 条答案" % len(answers))
    
    mode = input("请选择模式: 1=只做练习(在线练习)  2=只做考试(正式考试)  3=全都做: ").strip()
    
    score = 100.0
    duration = 5.0
    if mode in ("2", "3"):
        score_text = input("请输入正式考试目标分数(0-100, 默认100): ").strip()
        duration_text = input("请输入正式考试用时(分钟, 默认5): ").strip()
        try:
            score = float(score_text) if score_text else 100.0
            score = max(0.0, min(100.0, score))
        except ValueError:
            score = 100.0
        try:
            duration = float(duration_text) if duration_text else 5.0
        except ValueError:
            duration = 5.0
    
    session = make_session()
    
    if mode == "1":
        do_online_exams(session, answers)
    elif mode == "2":
        do_final_exam(session, answers, score, duration)
    else:
        do_online_exams(session, answers)
        do_final_exam(session, answers, score, duration)
    input("程序结束，感谢使用！")
