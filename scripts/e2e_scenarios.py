"""User-visible acceptance flows shared by the isolated browser runner."""

import re

from playwright.sync_api import expect


def run_scenarios(page, context, base_url, output):
    checks = []

    def visit(path, title):
        page.goto(base_url + path)
        page.wait_for_load_state("networkidle")
        expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()

    def field(label):
        control = page.get_by_role("dialog").get_by_label(re.compile("^" + re.escape(label)))
        if label == "币种":
            assert control.locator("option").evaluate_all("options => options.map(option => option.value)") == ["CNY", "USD"]
        return control

    def save(label="保存"):
        dialog = page.get_by_role("dialog")
        dialog.get_by_role("button", name=label, exact=True).click()
        expect(dialog).not_to_be_visible()
        page.wait_for_load_state("networkidle")

    def assert_fit():
        sizes = page.evaluate("({ viewport: innerWidth, content: document.documentElement.scrollWidth })")
        assert sizes["content"] <= sizes["viewport"] + 1, sizes

    visit("/", "财务总览")
    expect(page.get_by_text("从第一笔收支开始", exact=True)).to_be_visible()
    page.screenshot(path=str(output / "dashboard-empty.png"), full_page=True)
    checks.append("初始空数据总览正常，提供记账与目标入口")

    visit("/transactions", "收支记录")
    page.get_by_role("button", name="记一笔", exact=True).click()
    field("收支类型").select_option("income")
    field("金额").fill("1000")
    field("币种").select_option("USD")
    field("备注").fill("验收美元工资")
    save()
    row = page.get_by_role("row").filter(has_text="验收美元工资")
    expect(row).to_contain_text("1,000.00")
    expect(row).to_contain_text("7,200.00")
    checks.append("币种仅提供 CNY/USD，浏览器新增 USD 收入并正确折算双显")

    page.get_by_role("button", name="记一笔", exact=True).click()
    field("金额").fill("3500")
    field("备注").fill("验收家庭餐饮")
    save()
    row = page.get_by_role("row").filter(has_text="验收家庭餐饮")
    row.get_by_role("button", name="编辑餐饮记录", exact=True).click()
    field("金额").fill("3600")
    save()
    expect(row).to_contain_text("3,600.00")
    page.get_by_label("筛选收支类型").select_option("income")
    expect(page.get_by_role("row").filter(has_text="验收家庭餐饮")).to_have_count(0)
    expect(page.get_by_role("row").filter(has_text="验收美元工资")).to_have_count(1)
    page.get_by_role("button", name="清除筛选", exact=True).click()
    page.get_by_role("button", name="上个月", exact=True).click()
    expect(page.get_by_text("这个月还没有符合条件的记录", exact=True)).to_be_visible()
    page.get_by_role("button", name="下个月", exact=True).click()
    expect(page.get_by_role("row").filter(has_text="验收家庭餐饮")).to_have_count(1)
    checks.append("编辑支出、收支筛选与月份切换正确更新")

    page.get_by_role("button", name=re.compile("^周期规则")).click()
    page.get_by_role("button", name="新增规则", exact=True).click()
    field("金额").fill("88")
    field("分类").select_option("housing")
    field("每月几号").fill("18")
    field("备注").fill("验收周期房租")
    save()
    rule = page.get_by_role("row").filter(has_text="验收周期房租")
    rule.get_by_role("button", name="启用中", exact=True).click()
    expect(rule.get_by_role("button", name="已暂停", exact=True)).to_be_visible()
    rule.get_by_role("button", name="已暂停", exact=True).click()
    expect(rule.get_by_role("button", name="启用中", exact=True)).to_be_visible()
    page.get_by_role("button", name="收支明细", exact=True).click()
    expect(page.get_by_role("row").filter(has_text="验收周期房租")).to_have_count(1)
    page.reload()
    expect(page.get_by_role("row").filter(has_text="验收周期房租")).to_have_count(1)
    checks.append("周期规则创建、暂停、恢复和刷新保持一笔到期记录")

    visit("/budget", "预算管理")
    page.get_by_role("button", name="设置餐饮预算", exact=True).click()
    field("月度预算").fill("3000")
    save()
    card = page.locator("section.card").filter(has=page.get_by_role("heading", name="餐饮", exact=True))
    expect(card).to_contain_text("已超支")
    expect(card).to_contain_text("600.00")
    expect(card.get_by_role("progressbar")).to_have_attribute("aria-valuenow", "100")
    page.screenshot(path=str(output / "budget-desktop.png"), full_page=True)
    checks.append("预算超额显示金额、语义色和有界进度条")

    visit("/goals", "存款目标")
    page.get_by_role("button", name="新建目标", exact=True).click()
    field("目标名称").fill("六个月应急基金")
    field("目标金额").fill("10000")
    save()
    page.get_by_role("button", name="存入一笔", exact=True).click()
    field("金额").fill("100")
    field("币种").select_option("USD")
    save()
    page.get_by_role("button", name="存入一笔", exact=True).click()
    field("金额").fill("1280")
    save()
    expect(page.get_by_role("progressbar", name="六个月应急基金")).to_have_attribute("aria-valuenow", "20")
    page.get_by_role("button", name="六个月应急基金存入历史", exact=True).click()
    expect(page.get_by_role("dialog").get_by_role("row")).to_have_count(3)
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).not_to_be_visible()
    checks.append("目标两币种存入合并为20%进度，历史弹窗与Escape关闭有效")

    # Remaining product flows are defined separately so failures identify the area.
    _assets_dreams_investments(page, context, base_url, visit, field, save, checks)

    routes = [("/", "财务总览"), ("/transactions", "收支记录"), ("/budget", "预算管理"),
              ("/goals", "存款目标"), ("/assets", "资产分布"),
              ("/dreams", "Dream 清单"), ("/investments", "投资 Tracker")]
    for width in (1440, 390):
        page.set_viewport_size({"width": width, "height": 1000 if width == 1440 else 844})
        for route, title in routes:
            visit(route, title)
            assert_fit()
            slug = route.strip("/") or "dashboard"
            page.screenshot(path=str(output / f"{slug}-{width}.png"), full_page=True)
    checks.append("七个页面在1440px桌面与390px手机视口均可访问且无整页水平溢出")
    page.get_by_role("button", name="打开导航", exact=True).click()
    page.get_by_role("link", name="资产分布", exact=True).click()
    expect(page.get_by_role("heading", name="资产分布", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="打开导航", exact=True)).to_have_attribute("aria-expanded", "false")
    page.get_by_role("button", name="添加账户", exact=True).click()
    expect(page.get_by_role("dialog")).to_be_visible()
    for _ in range(12):
        page.keyboard.press("Tab")
        assert page.evaluate("!!document.activeElement.closest('[role=dialog]')"), "Modal focus escaped"
    page.get_by_role("dialog").get_by_role("button", name="保存", exact=True).click()
    expect(page.get_by_role("dialog")).to_be_visible()  # Empty required fields stop submission.
    assert_fit()
    page.screenshot(path=str(output / "asset-form-mobile.png"), full_page=True)
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).not_to_be_visible()
    checks.append("手机导航、表单必填校验、弹窗Tab焦点循环与Escape关闭正常")

    recovery = context.new_page()
    exceptions = []
    recovery.on("pageerror", lambda error: exceptions.append(str(error)))
    recovery.route("**/api/assets", lambda route: route.fulfill(status=503, content_type="application/json", body='{"detail":"验收模拟暂时不可用"}'))
    recovery.goto(base_url + "/assets")
    expect(recovery.get_by_role("alert")).to_contain_text("验收模拟暂时不可用")
    recovery.screenshot(path=str(output / "recoverable-error.png"), full_page=True)
    recovery.unroute("**/api/assets")
    recovery.get_by_role("button", name="重新加载", exact=True).click()
    expect(recovery.get_by_role("heading", name="日常储蓄账户", exact=True)).to_be_visible()
    assert not exceptions, exceptions
    recovery.close()
    checks.append("模拟503展示可恢复错误，重新加载后恢复实际资产数据")
    return {"passed": len(checks), "checks": checks, "screenshots": str(output),
            "expected_network_failures": ["错误恢复用例主动模拟一次 /api/assets 503"]}


def _assets_dreams_investments(page, context, base_url, visit, field, save, checks):
    visit("/assets", "资产分布")
    page.get_by_role("button", name="添加账户", exact=True).click()
    field("账户名称").fill("日常储蓄账户")
    field("账户余额").fill("120000")
    save()
    page.get_by_role("button", name="编辑日常储蓄账户", exact=True).click()
    field("账户余额").fill("125000")
    save()
    expect(page.locator(".account-card").filter(has_text="日常储蓄账户")).to_contain_text("125,000.00")
    page.get_by_role("button", name="添加账户", exact=True).click()
    field("账户名称").fill("待删除现金")
    field("资产类别").select_option("cash")
    field("账户余额").fill("1")
    save()
    page.get_by_role("button", name="删除待删除现金", exact=True).click()
    page.get_by_role("dialog").get_by_role("button", name="取消", exact=True).click()
    expect(page.get_by_role("heading", name="待删除现金", exact=True)).to_be_visible()
    page.get_by_role("button", name="删除待删除现金", exact=True).click()
    page.get_by_role("dialog").get_by_role("button", name="确认删除", exact=True).click()
    expect(page.get_by_role("heading", name="待删除现金", exact=True)).to_have_count(0)
    checks.append("资产账户新增、编辑、取消删除及确认删除更新真实余额")

    visit("/dreams", "Dream 清单")
    page.locator(".page-actions").get_by_role("button", name="添加心愿", exact=True).click()
    field("心愿名称").fill("旅行相机")
    field("预计价格").fill("6800")
    field("优先级").select_option("high")
    save()
    page.get_by_role("button", name="已购买", exact=True).click()
    field("实际支付金额").fill("6400")
    save("确认购买")
    page.get_by_role("button", name=re.compile("^已拥有")).click()
    expect(page.get_by_role("heading", name="旅行相机", exact=True)).to_be_visible()
    visit("/transactions", "收支记录")
    page.get_by_label("筛选来源").select_option("dream")
    row = page.get_by_role("row").filter(has_text="旅行相机")
    expect(row).to_have_count(1)
    expect(row).to_contain_text("6,400.00")
    checks.append("心愿按实付金额购买、归档，并联动一笔购物支出")

    visit("/investments", "投资 Tracker")
    page.get_by_role("button", name="添加标的", exact=True).click()
    field("名称").fill("沪深 300 ETF")
    field("代码").fill("510300")
    field("投资类型").select_option("etf")
    field("当前价格").fill("4")
    save()

    def trade(action, quantity, price, fee):
        page.get_by_role("button", name="记录买卖", exact=True).click()
        field("交易方向").select_option(action)
        field("成交数量").fill(str(quantity))
        field("成交价格").fill(str(price))
        field("交易费用").fill(str(fee))
        save()

    trade("buy", 1000, 3.75, 5)
    trade("buy", 1000, 4, 5)
    trade("sell", 500, 4.5, 2)
    holding = page.locator(".holdings-table").get_by_role("row").filter(has_text="沪深 300 ETF")
    expect(holding).to_contain_text("1,500")
    expect(holding).to_contain_text("3.88")
    page.get_by_label("沪深 300 ETF现价", exact=True).fill("4.2")
    page.get_by_role("button", name="保存沪深 300 ETF现价", exact=True).click()
    expect(holding).to_contain_text("6,300.00")
    expect(holding).to_contain_text("480.00")
    realized = page.locator(".metric").filter(has_text="累计已实现盈亏")
    expect(realized).to_contain_text("308.00")
    checks.append("含费买入、加仓、部分卖出及手动改价正确联动数量、均价与盈亏")

    visit("/", "财务总览")
    expect(page.locator(".wealth-amount")).to_contain_text("131,300.00")
    history_response = context.request.get(base_url + "/api/networth/history")
    assert history_response.ok, history_response.text()
    history = history_response.json()
    assert len(history) == 1 and history[0]["total_cny"] == 131300, history
    checks.append("Dashboard合并账户与投资，所有同日操作只产生一个净资产快照")
