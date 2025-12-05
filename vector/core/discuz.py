from vector.core.base import BaseProvider, HandlerResult
from typing import Dict, Optional, List
from bs4 import BeautifulSoup
import re
import random
import asyncio


class AuthenticationError(Exception):
    """登录认证异常"""

    pass


class BaseDiscuzProvider(BaseProvider):

    BASE_URL = None
    VIEW_COUNT = 11
    MIN_USER_COUNT = 2
    POKE_DEFAULT_NUM = 10
    POKE_DEFAULT_ICONID = 3

    # HTML清理正则表达式
    HTML_CLEANUP_PATTERN = re.compile(
        r"&#13;|<em>|</em>|\(前往兌換商城\)|<[^>]+>|\r?\n"
    )
    UID_PATTERN = re.compile(r"uid[=-]([0-9]+)")

    async def user_info(self, **request_kwargs) -> str:
        info_url = f"{self.base_url}/home.php?mod=spacecp&ac=credit&op=base"
        result = await self.request(info_url, **request_kwargs)

        soup = BeautifulSoup(result, "html.parser")
        creditl = soup.select_one(".creditl")

        if creditl:
            html = creditl.get_text()
            html = self.HTML_CLEANUP_PATTERN.sub("", html)
            html = html.strip()
            return "".join(html.split())
        return ""

    async def sign(
        self,
        sign_text: str = "您今天已經簽到過了",
        form_name: str = "#qiandao",
        **request_kwargs,
    ) -> str:
        sign_url = f"{self.base_url}/plugin.php?id=dsu_paulsign:sign"
        result = await self.request(sign_url, **request_kwargs)

        if sign_text in result:
            return sign_text

        soup = BeautifulSoup(result, "html.parser")
        params = await self._extract_form_params(soup, form_name)
        params["todaysay"] = "hello"

        form = soup.select_one(form_name)
        action_attr = form.get("action", "") if form else ""
        action = f"{self.base_url}/{action_attr.strip('/')}&inajax=1"
        response = await self.fetch(action, params, **request_kwargs)
        return await response.text()

    async def views(self, **request_kwargs) -> Optional[str]:
        """浏览用户空间 - 使用并发优化性能"""
        uid_list = await self.get_users(**request_kwargs)

        if not isinstance(uid_list, list) or len(uid_list) <= self.MIN_USER_COUNT:
            return "No users found"

        # 并发执行浏览请求
        tasks = []
        selected_uids = [random.choice(uid_list) for _ in range(self.VIEW_COUNT)]

        for uid in selected_uids:
            url = f"{self.base_url}/space-uid-{uid}.html"
            tasks.append(self.fetch(url, **request_kwargs))

        # 并发执行所有请求
        await asyncio.gather(*tasks)

        return f"Viewed {len(selected_uids)} user profiles"

    async def get_users(self, **request_kwargs) -> List[str]:
        user_url = (
            f"{self.base_url}/home.php?gender=0&startage=&endage="
            f"&avatarstatus=1&username=&searchsubmit=true&op=sex"
            f"&mod=spacecp&ac=search&type=base"
        )
        html = await self.request(user_url, **request_kwargs)

        soup = BeautifulSoup(html, "html.parser")
        elements = soup.select("ul.buddy li.bbda")
        user_id_list = []

        for element in elements:
            link_tag = element.select_one("div.avt a")
            if not link_tag:
                continue

            link = link_tag.get("href", "")
            if not link:
                continue

            uid_match = self.UID_PATTERN.search(link)
            if uid_match:
                user_id_list.append(uid_match.group(1))

        return user_id_list

    async def poke(
        self,
        success_text: str = "已發送",
        poke_num: int = None,
        iconid: int = None,
        **request_kwargs,
    ) -> List[str]:
        """打招呼功能 - 参数默认值和代码复用优化"""
        # 使用默认参数
        poke_num = poke_num or self.POKE_DEFAULT_NUM
        iconid = iconid or self.POKE_DEFAULT_ICONID

        uid_list = await self.get_users(**request_kwargs)
        if len(uid_list) <= self.MIN_USER_COUNT:
            return []

        result = []
        # 并发处理多个打招呼请求
        tasks = []
        selected_uids = [random.choice(uid_list) for _ in range(poke_num)]

        for uid in selected_uids:
            tasks.append(self._send_poke(uid, iconid, success_text, **request_kwargs))

        # 并发执行并收集结果
        poke_results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, poke_result in enumerate(poke_results):
            uid = selected_uids[i]
            if not isinstance(poke_result, Exception) and poke_result:
                result.append(f"用户 {uid} 的打招呼消息已发送。")

        return result

    async def _send_poke(
        self, uid: str, iconid: int, success_text: str, **request_kwargs
    ) -> bool:
        """发送单个打招呼请求的辅助方法"""
        poke_url = f"{self.base_url}/home.php?mod=spacecp&ac=poke&op=send&uid={uid}"
        text = await self.request(poke_url, **request_kwargs)

        soup = BeautifulSoup(text, "html.parser")
        params = await self._extract_form_params(soup, "#ct form")
        params["iconid"] = iconid
        params["note"] = "hello"

        action = f"{poke_url}&inajax=1"
        response = await self.fetch(action, params, **request_kwargs)
        response_text = await response.text()

        return success_text in response_text

    async def _extract_form_params(
        self, soup: BeautifulSoup, form_selector: str
    ) -> Dict[str, str]:
        """提取表单参数的公共方法"""
        form = soup.select_one(form_selector)
        params = {}

        if form:
            inputs = form.select("input")
            for _input in inputs:
                name = _input.get("name")
                value = _input.get("value", "")
                if name:  # 确保name不为None
                    params[name] = value or ""

        return params

    async def request(
        self,
        url: str,
        data: Optional[Dict] = None,
        method: str = "GET",
        **request_kwargs,
    ) -> str:
        """发送HTTP请求 - 优化异常处理"""
        response = await self.fetch(url, data, method, **request_kwargs)
        text = await response.text()

        if "action=logout" not in text:
            raise AuthenticationError("登录状态已失效，请重新登录")
        return text
