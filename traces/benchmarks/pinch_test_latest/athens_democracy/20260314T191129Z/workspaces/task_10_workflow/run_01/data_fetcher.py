#!/usr/bin/env python3
"""
API调用脚本 - DataFetcher
根据config.json配置调用API获取数据
"""

import json
import urllib.request
import urllib.error
import ssl
import sys

def main():
    # 配置参数
    config = {
        "api": {
            "endpoint": "https://api.example.com/v2/data",
            "method": "GET",
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            "timeout": 30
        }
    }
    
    endpoint = config["api"]["endpoint"]
    method = config["api"]["method"]
    headers = config["api"]["headers"]
    timeout = config["api"]["timeout"]
    
    print(f"Calling API: {method} {endpoint}")
    
    try:
        # 创建请求
        req = urllib.request.Request(endpoint, method=method)
        for key, value in headers.items():
            req.add_header(key, value)
        
        # 忽略SSL证书验证（仅用于测试环境）
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # 发送请求
        with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
            status_code = response.getcode()
            body = response.read().decode('utf-8')
            
            print(f"Status Code: {status_code}")
            print(f"Response: {body}")
            
            # 尝试解析JSON
            try:
                data = json.loads(body)
                print(f"Parsed JSON: {json.dumps(data, indent=2)}")
            except json.JSONDecodeError:
                print("Response is not valid JSON")
                
            return {"status": "success", "status_code": status_code, "body": body}
            
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        return {"status": "error", "error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        return {"status": "error", "error": str(e.reason)}
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    result = main()
    sys.exit(0 if result["status"] == "success" else 1)
