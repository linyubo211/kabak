import requests
import concurrent.futures
import os
import re
import random
import urllib3
import time

# 禁用安全请求警告（针对 https 证书过期的酒店源）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 配置区 ---
SOURCE_M3U = "py/all_channels.m3u"
CLEAN_M3U = "py/hotel_only.m3u"

# 🌟 优化参数：稍微延长超时时间，配合错峰延迟，并发控制在 25 既有速度又不易被酒店服务器拉黑
TIMEOUT = 8        
MAX_WORKERS = 25   

def is_hotel_source(url):
    """筛选酒店源关键词与黑名单过滤"""
    hotel_keywords = ['iptv/live', 'tsfile/live', '1000.json', 'key=txipt']
    blacklist = ['udp://', 'vip1.', '484947', 'rtp://', 'xinketongxun', '55555.io']
    
    url_l = url.lower()
    if any(word in url_l for word in blacklist):
        return False
    return any(word in url_l for word in hotel_keywords)

def check_url(name, url, group):
    """深度拨测逻辑：集成错峰延迟、多轮复活重试机制，大幅降低频道误杀率"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Connection': 'keep-alive'
    }
    
    # 提取 IP 部分用于日志展示 (例如 http://1.2.3.4:80/...)
    ip_display = url.split('/')[2] if len(url.split('/')) > 2 else url

    # 🌟 策略一：错峰出行。让线程随机小憩 0 到 1.5 秒，避免 25 个并发同时撞击同一个酒店 IP
    time.sleep(random.uniform(0, 1.5))

    max_retries = 3  # 🌟 策略二：给足 3 次机会（1次正赛 + 2次复活赛）
    for attempt in range(1, max_retries + 1):
        try:
            # 使用 GET + stream=True 读取音视频流片段进行真实拨测
            with requests.get(url, timeout=TIMEOUT, headers=headers, verify=False, stream=True) as r:
                if r.status_code == 200:
                    try:
                        # 尝试读取 1 字节数据，确认为真实可播流数据而非死链接
                        content_check = next(r.iter_content(chunk_size=1), None)
                        if content_check is not None:
                            if attempt > 1:
                                print(f"    ✨ [复活成功] {ip_display} -> {name} (第 {attempt} 次尝试成功)")
                            else:
                                print(f"    ✅ [成功] {ip_display} -> {name}")
                            return {"name": name, "url": url, "group": group}
                        else:
                            print(f"    ❌ [失败] {ip_display} (返回内容为空) - 尝试 {attempt}/{max_retries}")
                    except Exception as e:
                        print(f"    ❌ [失败] {ip_display} (数据流读取错: {e}) - 尝试 {attempt}/{max_retries}")
                else:
                    print(f"    ⚠️ [跳过] {ip_display} (状态码: {r.status_code}) - 尝试 {attempt}/{max_retries}")
        except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            print(f"    ⏰ [超时/网络错] {ip_display} ({type(e).__name__}) - 尝试 {attempt}/{max_retries}")
        
        # 如果不是最后一次尝试，稍微等待 1 秒再触发重试，避开网络瞬时拥堵
        if attempt < max_retries:
            time.sleep(1)
            
    return None

def main():
    if not os.path.exists(SOURCE_M3U):
        print(f"❌ 找不到输入文件: {SOURCE_M3U}")
        return

    tasks = []
    print(f"📂 正在读取并筛选酒店源任务...")
    
    with open(SOURCE_M3U, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 使用正则匹配 #EXTINF 和 紧随其后的 URL
    pattern = re.compile(r'(#EXTINF.*)\n(http.*)')
    matches = pattern.findall(content)
    
    for info, url in matches:
        url = url.strip()
        if is_hotel_source(url):
            # 提取频道名称
            name = "Unknown"
            if ',' in info:
                name = info.split(',')[-1].strip()
            
            # 提取分组名称
            group = "Hotel"
            group_match = re.search(r'group-title="([^"]+)"', info)
            if group_match:
                group = group_match.group(1)
                
            tasks.append((name, url, group))

    print(f"🚀 开始并发拨测 (并发数: {MAX_WORKERS}, 单次超时: {TIMEOUT}s, 最大重试: {max_retries})...")
    valid = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(check_url, *t) for t in tasks]
        
        count = 0
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            count += 1
            if res:
                valid.append(res)
                print(f"✅ [{len(valid)}] 发现有效源: {res['name']}")
            
            if count % 20 == 0:
                print(f"📡 已完成进度: {count}/{len(tasks)}")

    # 写入清洗完成后的 M3U 结果
    os.makedirs(os.path.dirname(CLEAN_M3U), exist_ok=True)
    with open(CLEAN_M3U, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for ch in valid:
            f.write(f'#EXTINF:-1 tvg-name="{ch["name"]}" group-title="{ch["group"]}",{ch["name"]}\n{ch["url"]}\n')
            
    print("-" * 30)
    print(f"✨ 清洗与深度拨测完全结束！")
    print(f"📊 扫描任务总数: {len(tasks)}")
    print(f"🎯 最终存活酒店源: {len(valid)}")
    print(f"💾 结果已保存至: {CLEAN_M3U}")

if __name__ == "__main__":
    main()
