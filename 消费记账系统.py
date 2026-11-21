# -*- coding: utf-8 -*-
"""
基于Python的大学生月度消费记账与预算预警系统

功能：消费记录增删改查、日期/类别查询、月度统计与环比、四类图表、
月总预算与分类预算分级预警、异常大额消费识别、TXT/HTML 月度报告、运行日志。

运行：python 消费记账系统.py
依赖：pandas、numpy、matplotlib、jinja2
"""

import json
import logging
import os
import sys
from datetime import datetime
from decimal import Decimal

import matplotlib
matplotlib.use('Agg')  # 只保存图片，不弹窗，保证无图形界面环境也能运行
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from jinja2 import Template

# ====================== 全局配置区 ======================
DATA_FILE = 'my_consume.csv'
BUDGET_FILE = 'my_budget.txt'
CAT_BUDGET_FILE = 'cat_budget.txt'
CATEGORIES = ['餐饮', '交通', '学习', '娱乐', '购物', '住宿', '医疗', '通讯', '其他']
PAGE_SIZE = 15
DEFAULT_BUDGET = 1500

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 日志初始化
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('app.log', encoding='utf-8'), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class DataManager:
    """消费记录的数据管理类：负责 CSV 读写、增删改查、筛选与分页。"""

    def __init__(self, filepath=DATA_FILE):
        self.filepath = filepath
        self.df = self.load_data()

    def _fill_id_for_old_data(self, df):
        """兼容旧版 CSV 没有 id 字段的情况，按行序补全自增 id。"""
        if 'id' not in df.columns or df['id'].isna().all():
            df['id'] = list(range(1, len(df) + 1))
        return df

    def _get_next_id(self):
        if len(self.df) == 0:
            return 1
        return int(self.df['id'].max()) + 1

    def load_data(self):
        """读取 CSV；文件不存在或为空时创建带表头的空表。"""
        columns = ['id', '日期', '类别', '金额', '备注']
        if not os.path.exists(self.filepath):
            df = pd.DataFrame(columns=columns)
            df.to_csv(self.filepath, index=False, encoding='utf-8-sig')
            return df
        try:
            df = pd.read_csv(self.filepath, dtype={'id': 'Int64', '金额': str})
        except pd.errors.EmptyDataError:
            df = pd.DataFrame(columns=columns)
            df.to_csv(self.filepath, index=False, encoding='utf-8-sig')
            return df
        df = self._fill_id_for_old_data(df)
        df['日期'] = pd.to_datetime(df['日期'])
        df['金额'] = df['金额'].apply(lambda x: Decimal(str(x)))
        return df

    def save_data(self):
        """把内存中的记录写回 CSV，金额转字符串以避免精度损失。"""
        try:
            save_df = self.df.copy()
            save_df['金额'] = save_df['金额'].astype(str)
            save_df.to_csv(self.filepath, index=False, encoding='utf-8-sig')
        except IOError as e:
            logger.error(f'保存文件失败 {e}')
            print('保存账单文件出错，请检查磁盘权限！')

    @staticmethod
    def is_valid_date(date_str):
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    def add_record(self, date_str, category, amount, note=''):
        """添加一条记录：日期、类别、金额三项校验通过后才写入。"""
        if not self.is_valid_date(date_str):
            print('日期格式错误，请使用 YYYY-MM-DD，月份1-12')
            return False
        if category not in CATEGORIES:
            print(f'类别不在预设列表中，请从以下选择：{CATEGORIES}')
            return False
        try:
            amount = Decimal(str(amount))
            if amount <= Decimal('0'):
                print('金额必须大于0')
                return False
        except Exception:
            print('金额必须是有效的正数数字')
            return False
        date = pd.to_datetime(date_str)
        new_id = self._get_next_id()
        new_row = pd.DataFrame([[new_id, date, category, amount, note]],
                               columns=['id', '日期', '类别', '金额', '备注'])
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        self.df = self.df.sort_values('日期').reset_index(drop=True)
        self.save_data()
        logger.info(f'添加记录 id={new_id}, {date_str} {category} {amount}元')
        print(f'记录添加成功：id={new_id} {date_str} {category} {amount}元')
        return True

    def modify_record_by_id(self, rec_id, new_date=None, new_cat=None, new_amount=None, new_note=None):
        """按 id 修改记录：先完成全部校验，再统一写入，避免校验失败时留下半改数据。"""
        mask = self.df['id'] == rec_id
        if not mask.any():
            print(f'找不到id={rec_id}的记录')
            return False
        idx = self.df[mask].index[0]
        updates = {}
        if new_date is not None:
            if not self.is_valid_date(new_date):
                print('日期格式错误')
                return False
            updates['日期'] = pd.to_datetime(new_date)
        if new_cat is not None:
            if new_cat not in CATEGORIES:
                print(f'类别非法，可选{CATEGORIES}')
                return False
            updates['类别'] = new_cat
        if new_amount is not None:
            try:
                val = Decimal(str(new_amount))
                if val <= 0:
                    print('金额必须大于0')
                    return False
                updates['金额'] = val
            except Exception:
                print('金额格式错误')
                return False
        if new_note is not None:
            updates['备注'] = new_note
        for key, value in updates.items():
            self.df.at[idx, key] = value
        self.df = self.df.sort_values('日期').reset_index(drop=True)
        self.save_data()
        logger.info(f'修改记录 id={rec_id}')
        print(f'id={rec_id}记录修改完成')
        return True

    def delete_record_by_id(self, rec_id):
        """按 id 删除记录，删除前二次确认。"""
        mask = self.df['id'] == rec_id
        if not mask.any():
            print(f'没有id={rec_id}的记录')
            return False
        deleted = self.df.loc[mask].iloc[0]
        confirm = input(
            f"确认删除 id={rec_id}: {deleted['日期'].strftime('%Y-%m-%d')} "
            f"{deleted['类别']} {deleted['金额']}元 ?(y/n): "
        ).strip().lower()
        if confirm != 'y':
            print('取消删除')
            return False
        self.df = self.df.drop(self.df[mask].index).reset_index(drop=True)
        self.save_data()
        logger.info(f'删除记录 id={rec_id}')
        print(f'已删除记录id={rec_id}：{deleted["日期"].strftime("%Y-%m-%d")} '
              f'{deleted["类别"]} {deleted["金额"]}元')
        return True

    def query_by_date_range(self, start_date, end_date):
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        mask = (self.df['日期'] >= start) & (self.df['日期'] <= end)
        return self.df[mask].sort_values('日期')

    def query_by_category(self, category):
        return self.df[self.df['类别'] == category].sort_values('日期')

    def get_month_data(self, year, month):
        mask = (self.df['日期'].dt.year == year) & (self.df['日期'].dt.month == month)
        return self.df[mask].sort_values('日期')

    def show_all(self, page=1):
        """分页显示全部记录，每页 PAGE_SIZE 条。"""
        total = len(self.df)
        if total == 0:
            print('暂无记录')
            return
        total_page = (total + PAGE_SIZE - 1) // PAGE_SIZE
        start = (page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
        page_data = self.df.iloc[start:end]
        print(f'\n====第 {page}/{total_page} 页，总{total}条记录====')
        for _, row in page_data.iterrows():
            print(f'id:{row["id"]:>3} | {row["日期"].strftime("%Y-%m-%d")} | '
                  f'{row["类别"]:<6} | {float(row["金额"]):>8.2f}元 | {row["备注"]}')
        if page < total_page:
            next_p = input('\n输入n看下一页，其他任意键退出浏览：').strip().lower()
            if next_p == 'n':
                self.show_all(page + 1)


class StatisticsAnalyzer:
    """统计分析类：总额、日均、分类汇总、占比、极值、环比、异常与预算核算。"""

    def __init__(self, data_manager):
        self.dm = data_manager
        self.df = data_manager.df

    def refresh(self):
        """数据增删改后刷新缓存的 DataFrame。"""
        self.df = self.dm.df

    def total_spending(self, data=None):
        if data is None:
            data = self.df
        return float(data['金额'].sum())

    def category_summary(self, data=None):
        if data is None:
            data = self.df
        if len(data) == 0:
            return pd.DataFrame(columns=['总金额', '笔数', '平均单笔'])
        df_copy = data.copy()
        df_copy['金额'] = df_copy['金额'].apply(float)
        result = df_copy.groupby('类别')['金额'].agg(['sum', 'count', 'mean']).sort_values('sum', ascending=False)
        result.columns = ['总金额', '笔数', '平均单笔']
        return result

    def daily_trend(self, data=None):
        if data is None:
            data = self.df
        if len(data) == 0:
            return pd.Series(dtype='float64')
        df_copy = data.copy()
        df_copy['金额'] = df_copy['金额'].apply(float)
        daily = df_copy.groupby(df_copy['日期'].dt.date)['金额'].sum()
        return daily

    def average_daily(self, data=None):
        if data is None:
            data = self.df
        if len(data) == 0:
            return 0
        days = data['日期'].dt.date.nunique()
        if days == 0:
            return 0
        return self.total_spending(data) / days

    def max_single(self, data=None):
        if data is None:
            data = self.df
        if len(data) == 0:
            return None
        df_copy = data.copy()
        df_copy['金额'] = df_copy['金额'].apply(float)
        idx = df_copy['金额'].idxmax()
        return data.loc[idx]

    def category_percentage(self, data=None):
        summary = self.category_summary(data)
        if len(summary) == 0:
            return pd.Series(dtype='float64')
        total = summary['总金额'].sum()
        return (summary['总金额'] / total * 100).round(2)

    def detect_anomalies(self, data=None, threshold=2.5):
        """基于均值—标准差识别异常大额消费，样本少于4条或标准差接近0时不判定。"""
        if data is None:
            data = self.df
        if len(data) < 4:
            return pd.DataFrame()
        df_copy = data.copy()
        df_copy['金额'] = df_copy['金额'].apply(float)
        mean_val = df_copy['金额'].mean()
        std_val = df_copy['金额'].std()
        if std_val < 1e-6:
            return pd.DataFrame()
        anomalies = data[np.abs(df_copy['金额'] - mean_val) > threshold * std_val]
        return anomalies

    def budget_check(self, budget, data=None):
        if data is None:
            data = self.df
        total = self.total_spending(data)
        remaining = budget - total
        usage_rate = total / budget * 100 if budget > 0 else 0
        return {
            '预算': budget,
            '已花费': total,
            '剩余': remaining,
            '使用率': round(usage_rate, 1),
            '是否超支': total > budget
        }

    def category_budget_check(self, cat_budget, data=None):
        """按类别核算预算执行情况，只统计设置了非零预算的类别。"""
        if data is None:
            data = self.df
        summary = self.category_summary(data)
        rows = []
        for cat, budget in cat_budget.items():
            budget = float(budget)
            if budget <= 0:
                continue
            spent = float(summary.loc[cat, '总金额']) if cat in summary.index else 0.0
            rate = spent / budget * 100 if budget > 0 else 0.0
            if spent > budget:
                status = '已超支'
            elif rate > 80:
                status = '即将超支'
            else:
                status = '正常'
            rows.append({'类别': cat, '预算': budget, '已花费': spent,
                         '剩余': budget - spent, '使用率': round(rate, 1), '状态': status})
        return pd.DataFrame(rows)

    def get_last_month_compare(self):
        """计算本月与上月的环比，处理 1 月跨年情况。"""
        now = datetime.now()
        if now.month == 1:
            last_year = now.year - 1
            last_month = 12
        else:
            last_year = now.year
            last_month = now.month - 1
        curr_data = self.dm.get_month_data(now.year, now.month)
        last_data = self.dm.get_month_data(last_year, last_month)
        curr_sum = self.total_spending(curr_data)
        last_sum = self.total_spending(last_data)
        rate = None
        if last_sum != 0:
            rate = round((curr_sum - last_sum) / last_sum * 100, 2)
        return {
            'curr_year': now.year, 'curr_month': now.month, 'curr_total': curr_sum,
            'last_year': last_year, 'last_month': last_month, 'last_total': last_sum,
            'change_rate': rate
        }


class Visualizer:
    """可视化类：绘制并保存类别饼图、每日柱状图、累计曲线和类别条形图。"""

    def __init__(self, analyzer):
        self.analyzer = analyzer

    def plot_category_pie(self, data=None, save_path='chart_pie.png'):
        summary = self.analyzer.category_summary(data)
        if len(summary) == 0:
            print('没有数据可画图')
            return
        plt.figure(figsize=(9, 6.6))
        colors = plt.cm.tab20(np.linspace(0, 1, len(summary)))
        wedges, _ = plt.pie(summary['总金额'].values,
                            labels=None,
                            startangle=90,
                            colors=colors,
                            explode=[0.02] * len(summary),
                            wedgeprops={'linewidth': 0.9, 'edgecolor': 'white'})
        pct = (summary['总金额'] / summary['总金额'].sum() * 100).round(1)
        legend_labels = [f'{cat}  {p:.1f}%' for cat, p in zip(summary.index, pct)]
        plt.legend(wedges, legend_labels, loc='center left', bbox_to_anchor=(0.96, 0.5),
                   fontsize=10, frameon=False, handlelength=1.2, labelspacing=0.8)
        plt.title('消费类别占比分布', fontsize=15, fontweight='bold')
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f'饼图已保存：{save_path}')

    def plot_daily_bar(self, data=None, save_path='chart_daily.png'):
        daily = self.analyzer.daily_trend(data)
        if len(daily) == 0:
            print('没有数据可画图')
            return
        plt.figure(figsize=(12, 5))
        plt.bar(range(len(daily)), daily.values, color='#66b3ff', edgecolor='white')
        plt.xticks(range(len(daily)), [str(d) for d in daily.index], rotation=45, ha='right')
        plt.title('每日消费柱状图', fontsize=14, fontweight='bold')
        plt.ylabel('消费金额（元）')
        plt.xlabel('日期')
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f'每日消费柱状图已保存：{save_path}')

    def plot_cumulative_line(self, data=None, budget=None, save_path='chart_cumulative.png'):
        daily = self.analyzer.daily_trend(data)
        if len(daily) == 0:
            print('没有数据可画图')
            return
        cumulative = daily.cumsum()
        plt.figure(figsize=(12, 5))
        plt.plot(range(len(cumulative)), cumulative.values, marker='o', linewidth=2, color='#e74c3c')
        plt.fill_between(range(len(cumulative)), cumulative.values, alpha=0.2, color='#e74c3c')
        if budget is not None and budget > 0:
            plt.axhline(y=budget, color='red', linestyle='--', label=f'月预算 {budget}元')
            plt.legend()
        plt.xticks(range(len(cumulative)), [str(d) for d in cumulative.index], rotation=45, ha='right')
        plt.title('累计消费趋势曲线', fontsize=14, fontweight='bold')
        plt.ylabel('累计金额（元）')
        plt.xlabel('日期')
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f'累计消费曲线图已保存：{save_path}')

    def plot_category_bar(self, data=None, save_path='chart_category.png'):
        summary = self.analyzer.category_summary(data)
        if len(summary) == 0:
            print('没有数据可画图')
            return
        plt.figure(figsize=(10, 6))
        colors = plt.cm.Set3(np.linspace(0, 1, len(summary)))
        bars = plt.barh(summary.index, summary['总金额'].values, color=colors, edgecolor='white')
        plt.title('各类别消费总额对比', fontsize=14, fontweight='bold')
        plt.xlabel('金额（元）')
        for bar in bars:
            width = bar.get_width()
            plt.text(width, bar.get_y() + bar.get_height() / 2.,
                     f'{width:.1f}', ha='left', va='center', fontsize=9)
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f'类别对比柱状图已保存：{save_path}')


class ReportGenerator:
    """报告生成类：把统计结果组织为 TXT 或 HTML 月度报告。"""

    def __init__(self, analyzer):
        self.analyzer = analyzer

    def generate_text_report(self, data=None, budget=None, cat_budget=None, title='消费分析报告'):
        if data is None:
            data = self.analyzer.df
        lines = []
        lines.append('=' * 50)
        lines.append(f'        {title}')
        lines.append('=' * 50)
        total = self.analyzer.total_spending(data)
        lines.append(f'总支出：{total:.2f} 元')
        avg = self.analyzer.average_daily(data)
        lines.append(f'日均支出：{avg:.2f} 元')
        days = data['日期'].dt.date.nunique() if len(data) > 0 else 0
        lines.append(f'记录天数：{days} 天')
        lines.append(f'总笔数：{len(data)} 笔')
        compare = self.analyzer.get_last_month_compare()
        lines.append(f'上月({compare["last_year"]}-{compare["last_month"]})总支出：{compare["last_total"]:.2f}元')
        if compare['change_rate'] is not None:
            lines.append(f'环比变化：{compare["change_rate"]}%')
        lines.append('')
        lines.append('--- 各类别支出明细 ---')
        summary = self.analyzer.category_summary(data)
        pct = self.analyzer.category_percentage(data)
        for cat in summary.index:
            lines.append(f'  {cat}：{summary.loc[cat, "总金额"]:>8.2f} 元  '
                         f'({summary.loc[cat, "笔数"]}笔, 占比{pct[cat]:.1f}%)')
        lines.append('')
        max_row = self.analyzer.max_single(data)
        if max_row is not None:
            lines.append(f'最大单笔：{float(max_row["金额"]):.2f} 元 '
                         f'({max_row["类别"]} - {max_row["备注"]})')
        anomalies = self.analyzer.detect_anomalies(data)
        if len(anomalies) > 0:
            lines.append('')
            lines.append('异常大额消费提醒：')
            for _, row in anomalies.iterrows():
                lines.append(f'  · {row["日期"].strftime("%Y-%m-%d")} '
                             f'{row["类别"]} {float(row["金额"]):.2f}元 - {row["备注"]}')
        if budget is not None:
            lines.append('')
            result = self.analyzer.budget_check(budget, data)
            lines.append('--- 预算执行情况 ---')
            lines.append(f'  月预算：{result["预算"]:.2f} 元')
            lines.append(f'  已花费：{result["已花费"]:.2f} 元')
            lines.append(f'  剩余：  {result["剩余"]:.2f} 元')
            lines.append(f'  使用率：{result["使用率"]}%')
            if result['是否超支']:
                lines.append(f'  已超支 {abs(result["剩余"]):.2f} 元！请注意控制')
            elif result['使用率'] > 80:
                lines.append('  预算使用率超过80%，即将超支')
            else:
                lines.append('  预算执行正常')
        if cat_budget:
            cat_result = self.analyzer.category_budget_check(cat_budget, data)
            if len(cat_result) > 0:
                lines.append('')
                lines.append('--- 分类预算执行情况 ---')
                for _, row in cat_result.iterrows():
                    lines.append(f'  {row["类别"]}：预算{row["预算"]:.2f}元，已花{row["已花费"]:.2f}元，'
                                 f'使用率{row["使用率"]}%，{row["状态"]}')
        lines.append('')
        lines.append('--- 智能建议 ---')
        food = data[data['类别'] == '餐饮']['金额'].sum()
        if total > 0:
            food_pct = float(food) / total * 100
            if food_pct < 15:
                lines.append('  · 餐饮占比偏低，注意合理饮食，不要为了省钱亏待自己')
            elif food_pct > 50:
                lines.append('  · 餐饮占比过高，试试自己做饭或选择更经济的就餐方式')
        shop = data[data['类别'] == '购物']['金额'].sum()
        if total > 0 and float(shop) / total > 0.4:
            lines.append('  · 购物支出占比过大，建议下单前列清单，避免冲动消费')
        ent = data[data['类别'] == '娱乐']['金额'].sum()
        if total > 0 and float(ent) / total > 0.2:
            lines.append('  · 娱乐开销偏高，试试免费或低成本的休闲方式')
        lines.append('=' * 50)
        report = '\n'.join(lines)
        print(report)
        with open('消费报告.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        print('\n报告已保存到：消费报告.txt')
        return report

    def generate_html_report(self, data, budget, title='消费报告'):
        html_template = Template("""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{{title}}</title>
<style>body{font-family:SimHei;max-width:900px;margin:20px auto;padding:10px;}</style>
</head>
<body>
<h1>{{title}}</h1>
<p>总支出：{{total}} 元</p>
<p>日均支出：{{avg}} 元</p>
<h3>类别明细</h3>
<table border="1" cellpadding="6">
<tr><th>类别</th><th>总金额</th><th>笔数</th><th>占比</th></tr>
{%for item in cat_list%}
<tr><td>{{item.cat}}</td><td>{{item.sum}}</td><td>{{item.count}}</td><td>{{item.pct}}%</td></tr>
{%endfor%}
</table>
<p>图表文件：chart_pie.png、chart_daily.png、chart_cumulative.png、chart_category.png</p>
</body>
</html>
""")
        total = self.analyzer.total_spending(data)
        avg = self.analyzer.average_daily(data)
        summary = self.analyzer.category_summary(data)
        pct = self.analyzer.category_percentage(data)
        cat_list = []
        for idx in summary.index:
            cat_list.append({
                'cat': idx,
                'sum': round(summary.loc[idx, '总金额'], 2),
                'count': summary.loc[idx, '笔数'],
                'pct': pct[idx]
            })
        html = html_template.render(title=title, total=round(total, 2), avg=round(avg, 2), cat_list=cat_list)
        with open('report.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print('HTML报告已生成 report.html')


def load_budget():
    try:
        if os.path.exists(BUDGET_FILE):
            with open(BUDGET_FILE, 'r', encoding='utf-8') as f:
                return float(f.read().strip())
    except (IOError, ValueError) as e:
        logger.error(f'读取预算文件异常{e}')
    return DEFAULT_BUDGET


def save_budget(budget):
    try:
        with open(BUDGET_FILE, 'w', encoding='utf-8') as f:
            f.write(str(budget))
    except IOError as e:
        logger.error(f'写入预算失败{e}')
        print('写入预算文件失败，请检查权限')


def load_cat_budget():
    if os.path.exists(CAT_BUDGET_FILE):
        try:
            with open(CAT_BUDGET_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {cat: 0 for cat in CATEGORIES}
    return {cat: 0 for cat in CATEGORIES}


def save_cat_budget(d):
    with open(CAT_BUDGET_FILE, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def print_menu():
    print('\n' + '=' * 45)
    print('      月度消费记录与分析系统')
    print('=' * 45)
    print('  1. 添加一条消费记录')
    print('  2. 查看所有记录(分页)')
    print('  3. 删除一条记录(输入id)')
    print('  4. 修改一条记录(输入id)')
    print('  5. 按日期范围查询')
    print('  6. 按类别查询')
    print('  7. 本月统计分析(含环比)')
    print('  8. 生成可视化图表')
    print('  9. 查看总预算执行情况')
    print(' 10. 设置月总预算')
    print(' 11. 设置分类预算')
    print(' 12. 生成完整月度报告(txt+html)')
    print('  0. 退出系统')
    print('=' * 45)


def main():
    dm = DataManager()
    analyzer = StatisticsAnalyzer(dm)
    visualizer = Visualizer(analyzer)
    reporter = ReportGenerator(analyzer)
    budget = load_budget()
    cat_budget = load_cat_budget()
    print(f'当前月总预算：{budget} 元')

    while True:
        print_menu()
        choice = input('请输入选项：').strip()

        if choice == '1':
            print('\n--- 添加消费记录 ---')
            date_str = input('日期（YYYY-MM-DD，回车默认今天）：').strip()
            if not date_str:
                date_str = datetime.now().strftime('%Y-%m-%d')
            print(f'可选类别：{CATEGORIES}')
            category = input('类别：').strip()
            amount = input('金额（元）：').strip()
            note = input('备注（可选）：').strip()
            if dm.add_record(date_str, category, amount, note):
                analyzer.refresh()

        elif choice == '2':
            print('\n--- 所有消费记录 ---')
            dm.show_all(page=1)

        elif choice == '3':
            print('\n--- 删除记录（输入记录id）---')
            dm.show_all(page=1)
            try:
                rid = int(input('输入待删除记录id：').strip())
                if dm.delete_record_by_id(rid):
                    analyzer.refresh()
            except ValueError:
                print('请输入数字ID')

        elif choice == '4':
            print('\n--- 修改记录，输入id，不修改直接回车留空 ---')
            dm.show_all(page=1)
            try:
                rid = int(input('输入要修改的id：').strip())
                d = input('新日期(YYYY-MM-DD，回车不修改)：').strip() or None
                c = input(f'新类别 {CATEGORIES}，回车不修改：').strip() or None
                a = input('新金额，回车不修改：').strip() or None
                n = input('新备注，回车不修改：').strip() or None
                if dm.modify_record_by_id(rid, new_date=d, new_cat=c, new_amount=a, new_note=n):
                    analyzer.refresh()
            except ValueError:
                print('id必须是数字')

        elif choice == '5':
            print('\n--- 按日期范围查询 ---')
            start = input('开始日期（YYYY-MM-DD）：').strip()
            end = input('结束日期（YYYY-MM-DD）：').strip()
            result = dm.query_by_date_range(start, end)
            if len(result) == 0:
                print('该时间段没有记录')
            else:
                show_df = result.copy()
                show_df['金额'] = show_df['金额'].apply(float)
                print(show_df.to_string(index=False))
                print(f'共 {len(result)} 笔，合计 {analyzer.total_spending(result):.2f} 元')

        elif choice == '6':
            print('\n--- 按类别查询 ---')
            print(f'可选类别：{CATEGORIES}')
            cat = input('输入类别：').strip()
            result = dm.query_by_category(cat)
            if len(result) == 0:
                print(f'没有 {cat} 类别的记录')
            else:
                show_df = result.copy()
                show_df['金额'] = show_df['金额'].apply(float)
                print(show_df.to_string(index=False))
                print(f'共 {len(result)} 笔，合计 {analyzer.total_spending(result):.2f} 元')

        elif choice == '7':
            print('\n--- 本月统计分析（含环比） ---')
            now = datetime.now()
            month_data = dm.get_month_data(now.year, now.month)
            cmp = analyzer.get_last_month_compare()
            print(f"上月{cmp['last_year']}-{cmp['last_month']}总支出：{cmp['last_total']:.2f}元")
            if cmp['change_rate'] is not None:
                print(f"环比变化 {cmp['change_rate']}%")
            if len(month_data) == 0:
                print('本月暂无记录')
            else:
                print(f'本月总支出：{analyzer.total_spending(month_data):.2f} 元')
                print(f'本月日均：{analyzer.average_daily(month_data):.2f} 元')
                summary = analyzer.category_summary(month_data)
                print('\n各类别汇总：')
                print(summary)

        elif choice == '8':
            print('\n--- 生成可视化图表 ---')
            now = datetime.now()
            month_data = dm.get_month_data(now.year, now.month)
            if len(month_data) == 0:
                print('本月暂无数据，生成全部数据图表')
                month_data = dm.df
            visualizer.plot_category_pie(month_data)
            visualizer.plot_daily_bar(month_data)
            visualizer.plot_cumulative_line(month_data, budget=budget)
            visualizer.plot_category_bar(month_data)
            print('所有图表已生成完毕！')

        elif choice == '9':
            print('\n--- 预算执行情况 ---')
            now = datetime.now()
            month_data = dm.get_month_data(now.year, now.month)
            result = analyzer.budget_check(budget, month_data)
            print(f'月预算：{result["预算"]:.2f} 元')
            print(f'已花费：{result["已花费"]:.2f} 元')
            print(f'剩余：  {result["剩余"]:.2f} 元')
            print(f'使用率：{result["使用率"]}%')
            if result['是否超支']:
                print(f'已超支 {abs(result["剩余"]):.2f} 元！')
            elif result['使用率'] > 80:
                print('即将超支，请注意控制消费')
            else:
                print('预算执行正常')
            cat_result = analyzer.category_budget_check(cat_budget, month_data)
            if len(cat_result) > 0:
                print('\n分类预算执行情况：')
                print(cat_result.to_string(index=False))

        elif choice == '10':
            print('\n--- 设置月总预算 ---')
            new_budget = input(f'当前预算 {budget} 元，输入新预算：').strip()
            try:
                budget = float(new_budget)
                save_budget(budget)
                print(f'预算已更新为：{budget} 元')
            except ValueError:
                print('请输入有效数字')

        elif choice == '11':
            print('\n--- 设置分类预算 ---')
            cat_budget = load_cat_budget()
            for c in CATEGORIES:
                val = input(f'{c} 当前预算{cat_budget[c]}，输入新预算(回车跳过)：').strip()
                if val:
                    try:
                        cat_budget[c] = float(val)
                    except ValueError:
                        print(f'{c}输入无效，跳过')
            save_cat_budget(cat_budget)
            print('分类预算保存完成')

        elif choice == '12':
            print('\n--- 生成完整月度报告(txt+html) ---')
            now = datetime.now()
            month_data = dm.get_month_data(now.year, now.month)
            if len(month_data) == 0:
                print('本月暂无记录，生成全部数据报告')
                month_data = dm.df
            reporter.generate_text_report(month_data, budget, cat_budget,
                                          title=f'{now.year}年{now.month}月消费报告')
            reporter.generate_html_report(month_data, budget, title=f'{now.year}年{now.month}月消费报告')

        elif choice == '0':
            print('感谢使用，再见！')
            break

        else:
            print('无效选项，请重新输入')


if __name__ == '__main__':
    main()
