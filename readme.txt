人工智能程序设计（Python）课程训练报告
配套程序说明文件（readme.txt）

一、项目名称
基于Python的大学生月度消费记账与预算预警系统

二、项目简介
本程序面向大学生生活费管理，使用Python实现消费记录的增、删、改、查、统计、可视化、预算预警和月度报告生成。数据保存在本地CSV、TXT、JSON文件中，不依赖数据库和网络。程序使用pandas做数据组织与分组统计，使用numpy做均值与标准差计算，使用matplotlib绘制图表，使用jinja2生成HTML报告。

三、运行环境
1. 操作系统：Windows 10/11、macOS或Linux。
2. Python版本：3.10及以上，开发和测试使用3.11。
3. 第三方库：pandas、numpy、matplotlib、jinja2，具体版本要求见requirements.txt。
4. 中文字体：Windows自带黑体；其他系统如显示方框，请安装SimHei字体。

四、目录与文件说明
1. 消费记账系统.py：主程序，包含DataManager、StatisticsAnalyzer、Visualizer、ReportGenerator四个类和main函数。
2. requirements.txt：第三方依赖清单。
3. README.md：项目说明文档，含安装、运行、复现和Git说明。
4. readme.txt：本文件，提交时单独附上。
5. my_consume.csv：消费记录数据，字段为id、日期、类别、金额、备注。
6. my_budget.txt：月总预算，内容为一个数字，示例为1500。
7. cat_budget.txt：分类预算，JSON格式，键为类别、值为预算金额。
8. 运行示例文件夹：保存一次完整运行生成的四张图表、TXT报告、HTML报告和日志，可用于核对运行结果。
9. 报告文件夹：课程训练报告Word文档。

五、安装与运行方法
Windows PowerShell下依次执行：
cd 2025213171韩文涛基于Python的大学生月度消费记账与预算预警系统
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python 消费记账系统.py

macOS或Linux下依次执行：
cd 2025213171韩文涛基于Python的大学生月度消费记账与预算预警系统
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python 消费记账系统.py

运行后按屏幕菜单输入数字选择功能，输入0退出。退出虚拟环境使用deactivate命令。

六、功能菜单
1. 添加消费记录
2. 查看全部记录（每页15条）
3. 删除记录（按id，需二次确认）
4. 修改记录（按id，先校验后写入）
5. 按日期范围查询
6. 按类别查询
7. 本月统计分析
8. 生成图表（类别饼图、每日柱状图、累计趋势图、类别条形图）
9. 预算执行情况（月总预算与分类预算）
10. 设置月总预算
11. 设置分类预算
12. 生成月度报告（TXT和HTML）
0. 退出程序

七、数据文件格式
my_consume.csv表头必须为：id,日期,类别,金额,备注。
日期格式为YYYY-MM-DD；类别必须是餐饮、交通、学习、娱乐、购物、住宿、医疗、通讯、其他之一；金额必须为正数；备注可以为空。
my_budget.txt只写一个数字，例如1500。
cat_budget.txt为JSON对象，例如：
{"餐饮": 600, "交通": 80, "学习": 250, "娱乐": 100, "购物": 300, "住宿": 150, "医疗": 100, "通讯": 60, "其他": 50}

八、复现步骤
1. 按第五步创建虚拟环境并安装依赖。
2. 保持数据文件与程序在同一目录。
3. 运行程序，依次选择7、8、9、12，得到统计结果、四张图表、预算执行情况和月度报告。
4. 若要从空数据开始，删除my_consume.csv后重新运行，程序会自动建立空表。
5. 运行示例文件夹中的结果对应26笔记录、合计1018元、日均56.56元、预算使用率67.9%，可用于核对。

九、Git版本控制说明
本项目使用Git管理源码和文档，.gitignore已排除虚拟环境、字节码缓存和根目录临时输出。
常用命令：
git status
git add .
git commit -m "描述本次修改"
git log --oneline

远程仓库：
git remote add origin https://github.com/hhh221114/consumption-ledger.git
git branch -M main
git push -u origin main


十、注意事项
1. 程序所有数据均保存在本地，不会上传网络。
2. 图表使用Agg后端保存为PNG文件，不弹窗显示。
3. 金额内部使用Decimal保存，避免浮点误差。
4. 异常消费判定使用均值加减2.5倍标准差，样本少于4条或标准差接近0时不判定。
5. 示例数据为虚构的2026年11月消费记录，仅用于演示。


