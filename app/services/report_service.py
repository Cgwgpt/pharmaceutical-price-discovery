"""
报告生成服务
生成每日监控报告、价格分析报告等
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from config import DATABASE_URL
from app.models import Drug, PriceRecord, init_db


class ReportService:
    """
    报告生成服务
    
    功能:
    - 每日监控报告
    - 价格分析报告
    - 采购建议报告
    """
    
    REPORT_DIR = 'reports'
    
    def __init__(self):
        self.engine, SessionLocal = init_db(DATABASE_URL)
        self.session = SessionLocal()
        
        # 确保报告目录存在
        if not os.path.exists(self.REPORT_DIR):
            os.makedirs(self.REPORT_DIR)
    
    def __del__(self):
        if hasattr(self, 'session') and self.session:
            self.session.close()
    
    def generate_daily_report(self, summary: Dict[str, Any] = None) -> str:
        """
        生成每日监控报告
        
        Args:
            summary: 监控汇总数据
            
        Returns:
            报告文件路径
        """
        if summary is None:
            from app.services.monitor_service import MonitorService
            monitor = MonitorService()
            summary = monitor.get_daily_summary()
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        report_name = f'daily_report_{date_str}.md'
        report_path = os.path.join(self.REPORT_DIR, report_name)
        
        # 生成报告内容
        content = self._generate_daily_report_content(summary, date_str)
        
        # 保存报告
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return report_path
    
    def _generate_daily_report_content(self, summary: Dict, date_str: str) -> str:
        """生成每日报告内容"""
        content = f"""# 医药价格监控日报

## 日期: {date_str}

---

## 📊 数据概览

| 指标 | 数值 |
|-----|------|
| 今日爬取记录 | {summary.get('crawled_count', 0)} 条 |
| 价格变动告警 | {summary.get('alert_count', 0)} 条 |
| 价格上涨 | {summary.get('price_up_count', 0)} 条 |
| 价格下降 | {summary.get('price_down_count', 0)} 条 |

---

## 📈 数据来源统计

"""
        # 来源统计
        sources = summary.get('sources', [])
        if sources:
            content += "| 来源 | 记录数 |\n|-----|------|\n"
            for source in sources:
                content += f"| {source['name']} | {source['count']} |\n"
        else:
            content += "暂无数据\n"
        
        content += "\n---\n\n## 🔔 价格变动告警 (Top 10)\n\n"
        
        # 告警列表
        alerts = summary.get('top_alerts', [])
        if alerts:
            content += "| 药品名称 | 原价 | 现价 | 变动 | 来源 |\n"
            content += "|---------|-----|-----|-----|-----|\n"
            for alert in alerts[:10]:
                direction = '↓' if alert.get('direction') == 'down' else '↑'
                content += f"| {alert.get('drug_name', '-')} | ¥{alert.get('previous_price', 0):.2f} | ¥{alert.get('current_price', 0):.2f} | {direction} {abs(alert.get('change_percent', 0)):.1f}% | {alert.get('source_name', '-')} |\n"
        else:
            content += "暂无价格变动告警\n"
        
        content += f"""
---

## 📝 备注

- 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 价格变动阈值: 5%
- 数据仅供参考，请以实际采购价格为准

---

*医药价格发现系统自动生成*
"""
        return content
    
    def generate_price_analysis_report(self, drug_name: str, days: int = 30) -> str:
        """
        生成药品价格分析报告
        
        Args:
            drug_name: 药品名称
            days: 分析天数
            
        Returns:
            报告文件路径
        """
        from app.services.compare_service import CompareService
        from app.services.monitor_service import MonitorService
        from app.services.recommendation_service import RecommendationService
        
        compare = CompareService()
        monitor = MonitorService()
        recommend = RecommendationService()
        
        # 获取数据
        comparison = compare.compare_prices(drug_name)
        
        if not comparison:
            return None
        
        drug_id = comparison['prices'][0]['drug_id'] if comparison['prices'] else None
        trend = monitor.get_price_trend(drug_id, days) if drug_id else {}
        recommendation = recommend.get_recommendation(drug_name)
        
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = drug_name.replace('/', '_').replace('\\', '_')
        report_name = f'price_analysis_{safe_name}_{date_str}.md'
        report_path = os.path.join(self.REPORT_DIR, report_name)
        
        content = self._generate_price_analysis_content(
            drug_name, comparison, trend, recommendation, days
        )
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return report_path
    
    def _generate_price_analysis_content(
        self,
        drug_name: str,
        comparison: Dict,
        trend: Dict,
        recommendation: Dict,
        days: int
    ) -> str:
        """生成价格分析报告内容"""
        content = f"""# 药品价格分析报告

## 药品: {drug_name}

---

## 📊 价格概览

| 指标 | 数值 |
|-----|------|
| 最低价 | ¥{comparison.get('lowest_price', 0):.2f} |
| 最高价 | ¥{comparison.get('highest_price', 0):.2f} |
| 平均价 | ¥{comparison.get('average_price', 0):.2f} |
| 价差 | {comparison.get('price_diff_percent', 0):.1f}% |
| 数据来源数 | {comparison.get('source_count', 0)} |

---

## 📈 价格趋势 (近{days}天)

| 指标 | 数值 |
|-----|------|
| 趋势 | {self._translate_trend(trend.get('trend', 'unknown'))} |
| 波动率 | {trend.get('volatility', 0):.1f}% |
| 最低价 | ¥{trend.get('min_price', 0):.2f} |
| 最高价 | ¥{trend.get('max_price', 0):.2f} |
| 数据点数 | {trend.get('data_points', 0)} |

---

## 💰 各平台价格对比

"""
        # 价格列表
        prices = comparison.get('prices', [])
        if prices:
            content += "| 排名 | 来源 | 价格 | 规格 | 厂家 |\n"
            content += "|-----|-----|-----|-----|-----|\n"
            for i, p in enumerate(prices, 1):
                badge = "🏆" if i == 1 else str(i)
                content += f"| {badge} | {p.get('source_name', '-')} | ¥{p.get('price', 0):.2f} | {p.get('specification', '-')} | {p.get('manufacturer', '-')[:20] if p.get('manufacturer') else '-'} |\n"
        
        content += "\n---\n\n## 🎯 采购建议\n\n"
        
        if recommendation:
            content += f"""
**综合评分**: {recommendation.get('overall_score', 0)}/100

**推荐渠道**: {recommendation.get('best_channel', {}).get('source', '-')}

**推荐价格**: ¥{recommendation.get('best_channel', {}).get('price', 0):.2f}

**建议**:
"""
            for rec in recommendation.get('recommendations', []):
                priority_icon = '🔴' if rec['priority'] == 'high' else ('🟡' if rec['priority'] == 'medium' else '🟢')
                content += f"- {priority_icon} {rec['message']}\n"
        
        content += f"""
---

## 📝 备注

- 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 分析周期: {days}天
- 数据仅供参考，请以实际采购价格为准

---

*医药价格发现系统自动生成*
"""
        return content
    
    def _translate_trend(self, trend: str) -> str:
        """翻译趋势"""
        translations = {
            'rising': '📈 上涨',
            'falling': '📉 下降',
            'stable': '➡️ 稳定',
            'unknown': '❓ 未知',
            'insufficient_data': '⚠️ 数据不足'
        }
        return translations.get(trend, trend)
    
    def generate_procurement_report(self, drug_list: List[Dict]) -> str:
        """
        生成采购建议报告
        
        Args:
            drug_list: 药品列表 [{'name': '药品名', 'quantity': 数量}, ...]
            
        Returns:
            报告文件路径
        """
        from app.services.recommendation_service import RecommendationService
        
        recommend = RecommendationService()
        batch_result = recommend.get_batch_recommendations(drug_list)
        
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_name = f'procurement_report_{date_str}.md'
        report_path = os.path.join(self.REPORT_DIR, report_name)
        
        content = self._generate_procurement_content(batch_result)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return report_path
    
    def _generate_procurement_content(self, batch_result: Dict) -> str:
        """生成采购建议报告内容"""
        content = f"""# 采购建议报告

## 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 汇总

| 指标 | 数值 |
|-----|------|
| 药品数量 | {batch_result.get('total_items', 0)} |
| 潜在节省 | ¥{batch_result.get('total_potential_savings', 0):.2f} |

---

## 💊 详细建议

"""
        recommendations = batch_result.get('recommendations', [])
        
        for i, rec in enumerate(recommendations, 1):
            content += f"""
### {i}. {rec.get('drug_name', '-')}

| 指标 | 数值 |
|-----|------|
| 综合评分 | {rec.get('overall_score', 0)}/100 |
| 推荐渠道 | {rec.get('best_channel', {}).get('source', '-')} |
| 推荐价格 | ¥{rec.get('best_channel', {}).get('price', 0):.2f} |
| 稳定性 | {rec.get('stability_analysis', {}).get('stability_level', '-')} |

"""
        
        content += """
---

## 📝 备注

- 数据仅供参考，请以实际采购价格为准
- 建议在采购前再次确认价格

---

*医药价格发现系统自动生成*
"""
        return content
    
    def list_reports(self, report_type: str = None) -> List[Dict]:
        """
        列出所有报告
        
        Args:
            report_type: 报告类型 (daily, price_analysis, procurement)
            
        Returns:
            报告列表
        """
        reports = []
        
        if not os.path.exists(self.REPORT_DIR):
            return reports
        
        for filename in os.listdir(self.REPORT_DIR):
            if not filename.endswith('.md'):
                continue
            
            if report_type:
                if report_type == 'daily' and not filename.startswith('daily_report'):
                    continue
                if report_type == 'price_analysis' and not filename.startswith('price_analysis'):
                    continue
                if report_type == 'procurement' and not filename.startswith('procurement_report'):
                    continue
            
            filepath = os.path.join(self.REPORT_DIR, filename)
            stat = os.stat(filepath)
            
            reports.append({
                'filename': filename,
                'path': filepath,
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        # 按修改时间排序
        reports.sort(key=lambda x: x['modified_at'], reverse=True)
        
        return reports
