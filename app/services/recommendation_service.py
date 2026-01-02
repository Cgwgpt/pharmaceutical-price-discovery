"""
采购建议服务
实现最优渠道推荐、节省金额计算和价格稳定性分析
"""
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from config import DATABASE_URL
from app.models import Drug, PriceRecord, init_db
from app.services.compare_service import CompareService
from app.services.monitor_service import MonitorService


class RecommendationService:
    """
    采购建议服务
    
    功能:
    - 最优渠道推荐
    - 节省金额计算
    - 价格稳定性分析
    - 综合采购建议
    """
    
    def __init__(self):
        self.engine, SessionLocal = init_db(DATABASE_URL)
        self.session = SessionLocal()
        self.compare_service = CompareService()
        self.monitor_service = MonitorService()
    
    def __del__(self):
        if hasattr(self, 'session') and self.session:
            self.session.close()
    
    def get_best_channel(self, drug_name: str) -> Optional[Dict[str, Any]]:
        """
        获取最优采购渠道
        
        Args:
            drug_name: 药品名称
            
        Returns:
            最优渠道信息
        """
        comparison = self.compare_service.compare_prices(drug_name)
        
        if not comparison or not comparison['prices']:
            return None
        
        best = comparison['prices'][0]  # 已按价格排序，第一个是最低价
        
        return {
            'drug_name': drug_name,
            'best_source': best['source_name'],
            'best_price': best['price'],
            'source_url': best['source_url'],
            'specification': best.get('specification', ''),
            'manufacturer': best.get('manufacturer', ''),
            'compared_sources': comparison['source_count'],
            'savings_vs_highest': comparison['potential_savings'],
            'savings_percent': comparison['price_diff_percent']
        }
    
    def calculate_savings(
        self, 
        drug_name: str, 
        quantity: int,
        current_source: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        计算采购节省金额
        
        Args:
            drug_name: 药品名称
            quantity: 采购数量
            current_source: 当前采购渠道（可选）
            
        Returns:
            节省金额信息
        """
        comparison = self.compare_service.compare_prices(drug_name)
        
        if not comparison:
            return None
        
        lowest_price = comparison['lowest_price']
        highest_price = comparison['highest_price']
        
        # 如果指定了当前渠道，计算相对于当前渠道的节省
        current_price = highest_price
        if current_source:
            for p in comparison['prices']:
                if p['source_name'] == current_source:
                    current_price = p['price']
                    break
        
        unit_savings = current_price - lowest_price
        total_savings = unit_savings * quantity
        
        return {
            'drug_name': drug_name,
            'quantity': quantity,
            'current_source': current_source,
            'current_unit_price': round(current_price, 2),
            'best_unit_price': round(lowest_price, 2),
            'unit_savings': round(unit_savings, 2),
            'total_current_cost': round(current_price * quantity, 2),
            'total_best_cost': round(lowest_price * quantity, 2),
            'total_savings': round(total_savings, 2),
            'savings_percent': round((unit_savings / current_price) * 100, 2) if current_price > 0 else 0,
            'best_source': comparison.get('best_source') or comparison.get('best_manufacturer') or (comparison['prices'][0]['source_name'] if comparison.get('prices') else None)
        }
    
    def analyze_price_stability(self, drug_id: int, days: int = 30) -> Dict[str, Any]:
        """
        分析价格稳定性
        
        Args:
            drug_id: 药品ID
            days: 分析天数
            
        Returns:
            稳定性分析结果
        """
        trend = self.monitor_service.get_price_trend(drug_id, days)
        
        # 稳定性评分（0-100，越高越稳定）
        volatility = trend.get('volatility', 0)
        
        if volatility < 2:
            stability_score = 95
            stability_level = '非常稳定'
        elif volatility < 5:
            stability_score = 80
            stability_level = '稳定'
        elif volatility < 10:
            stability_score = 60
            stability_level = '一般'
        elif volatility < 20:
            stability_score = 40
            stability_level = '波动较大'
        else:
            stability_score = 20
            stability_level = '波动剧烈'
        
        return {
            'drug_id': drug_id,
            'stability_score': stability_score,
            'stability_level': stability_level,
            'volatility': volatility,
            'trend': trend['trend'],
            'min_price': trend.get('min_price', 0),
            'max_price': trend.get('max_price', 0),
            'avg_price': trend.get('avg_price', 0),
            'data_points': trend.get('data_points', 0),
            'period_days': days
        }
    
    def get_recommendation(self, drug_name: str, quantity: int = 1) -> Optional[Dict[str, Any]]:
        """
        获取综合采购建议
        
        综合考虑价格、稳定性、来源可靠性等因素
        
        Args:
            drug_name: 药品名称
            quantity: 采购数量
            
        Returns:
            综合采购建议
        """
        # 优先使用原名搜索
        comparison = self.compare_service.compare_prices(drug_name)
        generic_name = drug_name  # 默认使用原名
        
        # 如果原名没找到，尝试标准化后搜索
        if not comparison or not comparison['prices']:
            from app.services.normalize_service import NormalizeService
            normalize = NormalizeService()
            generic_name = normalize.get_generic_name(drug_name)
            if generic_name != drug_name:
                comparison = self.compare_service.compare_prices(generic_name)
        
        if not comparison or not comparison['prices']:
            return None
        
        # 获取药品ID
        drug = self.session.query(Drug).filter(
            Drug.name.ilike(f'%{drug_name}%')
        ).first()
        
        if not drug and generic_name != drug_name:
            drug = self.session.query(Drug).filter(
                Drug.name.ilike(f'%{generic_name}%')
            ).first()
        
        if not drug:
            return None
        
        # 分析价格稳定性
        stability = self.analyze_price_stability(drug.id)
        
        # 计算节省金额
        savings = self.calculate_savings(drug_name, quantity)
        
        # 生成建议
        recommendations = []
        
        # 获取最优来源
        best_source = comparison.get('best_source') or comparison.get('best_manufacturer') or (comparison['prices'][0]['source_name'] if comparison.get('prices') else '未知')
        
        # 价格建议
        if comparison['price_diff_percent'] > 10:
            recommendations.append({
                'type': 'price',
                'priority': 'high',
                'message': f"价差较大({comparison['price_diff_percent']}%)，建议从{best_source}采购，可节省¥{comparison['potential_savings']:.2f}/单位"
            })
        elif comparison['price_diff_percent'] > 5:
            recommendations.append({
                'type': 'price',
                'priority': 'medium',
                'message': f"存在一定价差({comparison['price_diff_percent']}%)，可考虑更换渠道"
            })
        else:
            recommendations.append({
                'type': 'price',
                'priority': 'low',
                'message': "各渠道价格相近，可根据其他因素选择"
            })
        
        # 稳定性建议
        if stability['stability_score'] < 50:
            recommendations.append({
                'type': 'stability',
                'priority': 'high',
                'message': f"价格波动较大({stability['volatility']:.1f}%)，建议关注价格走势后再采购"
            })
        elif stability['stability_score'] >= 80:
            recommendations.append({
                'type': 'stability',
                'priority': 'low',
                'message': f"价格稳定({stability['stability_level']})，可放心采购"
            })
        
        # 趋势建议
        if stability['trend'] == 'falling':
            recommendations.append({
                'type': 'trend',
                'priority': 'medium',
                'message': "价格呈下降趋势，可考虑等待更低价格或分批采购"
            })
        elif stability['trend'] == 'rising':
            recommendations.append({
                'type': 'trend',
                'priority': 'high',
                'message': "价格呈上涨趋势，建议尽快采购锁定当前价格"
            })
        
        # 批量采购建议
        if quantity > 10 and savings and savings['total_savings'] > 100:
            recommendations.append({
                'type': 'bulk',
                'priority': 'high',
                'message': f"批量采购{quantity}单位可节省¥{savings['total_savings']:.2f}"
            })
        
        # 同药不同名提示
        if generic_name != drug_name:
            recommendations.append({
                'type': 'alias',
                'priority': 'info',
                'message': f"'{drug_name}'的通用名为'{generic_name}'，已按通用名搜索比价"
            })
        
        # 综合评分
        price_score = max(0, 100 - comparison['price_diff_percent'] * 2)
        overall_score = (price_score + stability['stability_score']) / 2
        
        # 采购时机建议
        timing_advice = self._get_timing_advice(stability, comparison)
        
        return {
            'drug_name': drug_name,
            'generic_name': generic_name,
            'drug_id': drug.id,
            'quantity': quantity,
            'overall_score': round(overall_score, 1),
            'timing_advice': timing_advice,
            'best_channel': {
                'source': best_source,
                'price': comparison['lowest_price'],
                'url': comparison['prices'][0]['source_url'] if comparison['prices'] else None
            },
            'price_analysis': {
                'lowest': comparison['lowest_price'],
                'highest': comparison['highest_price'],
                'average': comparison['average_price'],
                'diff_percent': comparison['price_diff_percent'],
                'source_count': comparison.get('source_count') or comparison.get('total_records', 0)
            },
            'stability_analysis': stability,
            'savings_analysis': savings,
            'recommendations': recommendations,
            'generated_at': datetime.now().isoformat()
        }
    
    def _get_timing_advice(self, stability: Dict, comparison: Dict) -> Dict[str, Any]:
        """
        获取采购时机建议
        
        Args:
            stability: 稳定性分析
            comparison: 比价结果
            
        Returns:
            时机建议
        """
        trend = stability.get('trend', 'unknown')
        volatility = stability.get('volatility', 0)
        diff_percent = comparison.get('price_diff_percent', 0)
        
        if trend == 'falling' and volatility < 10:
            return {
                'advice': '观望',
                'reason': '价格下降趋势明显，建议等待更低价格',
                'urgency': 'low'
            }
        elif trend == 'rising' and diff_percent > 10:
            return {
                'advice': '立即采购',
                'reason': '价格上涨且存在较大价差，建议立即从最低价渠道采购',
                'urgency': 'high'
            }
        elif volatility > 20:
            return {
                'advice': '分批采购',
                'reason': '价格波动剧烈，建议分批采购降低风险',
                'urgency': 'medium'
            }
        elif diff_percent > 15:
            return {
                'advice': '立即采购',
                'reason': f'价差达{diff_percent:.1f}%，建议立即从最低价渠道采购',
                'urgency': 'high'
            }
        else:
            return {
                'advice': '正常采购',
                'reason': '价格稳定，可按需采购',
                'urgency': 'normal'
            }
    
    def get_batch_recommendations(
        self, 
        drug_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量获取采购建议
        
        Args:
            drug_list: 药品列表 [{'name': '药品名', 'quantity': 数量}, ...]
            
        Returns:
            批量建议列表
        """
        results = []
        total_savings = 0
        
        for item in drug_list:
            drug_name = item.get('name', '')
            quantity = item.get('quantity', 1)
            
            if not drug_name:
                continue
            
            recommendation = self.get_recommendation(drug_name, quantity)
            
            if recommendation:
                results.append(recommendation)
                if recommendation.get('savings_analysis'):
                    total_savings += recommendation['savings_analysis'].get('total_savings', 0)
        
        return {
            'recommendations': results,
            'total_items': len(results),
            'total_potential_savings': round(total_savings, 2),
            'generated_at': datetime.now().isoformat()
        }
    
    def get_top_savings_opportunities(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取节省金额最大的采购机会
        
        Args:
            limit: 返回数量
            
        Returns:
            机会列表
        """
        ranking = self.compare_service.get_price_ranking(limit * 2)
        
        opportunities = []
        for item in ranking:
            drug = self.session.query(Drug).filter(Drug.id == item['drug_id']).first()
            if not drug:
                continue
            
            stability = self.analyze_price_stability(drug.id)
            
            opportunities.append({
                'drug_id': item['drug_id'],
                'drug_name': item['drug_name'],
                'lowest_price': item['lowest_price'],
                'highest_price': item['highest_price'],
                'diff_percent': item['diff_percent'],
                'potential_savings': item['potential_savings'],
                'best_source': item['best_source'],
                'stability_score': stability['stability_score'],
                'stability_level': stability['stability_level'],
                'recommendation': '强烈推荐' if item['diff_percent'] > 15 and stability['stability_score'] > 60 else '推荐'
            })
        
        return opportunities[:limit]
