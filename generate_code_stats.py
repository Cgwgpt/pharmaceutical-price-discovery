"""
生成代码统计报告
"""
import os
from pathlib import Path
from collections import defaultdict

def count_lines(file_path):
    """统计文件行数"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            code_lines = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
            comment_lines = len([l for l in lines if l.strip().startswith('#')])
            blank_lines = len([l for l in lines if not l.strip()])
            return len(lines), code_lines, comment_lines, blank_lines
    except:
        return 0, 0, 0, 0

def analyze_directory(root_dir, extensions):
    """分析目录"""
    stats = defaultdict(lambda: {'files': 0, 'total': 0, 'code': 0, 'comment': 0, 'blank': 0})
    
    exclude_dirs = {'venv', '.hypothesis', '.pytest_cache', '__pycache__', '.git', 'node_modules'}
    
    for root, dirs, files in os.walk(root_dir):
        # 排除目录
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        # 获取相对路径
        rel_path = os.path.relpath(root, root_dir)
        if rel_path == '.':
            module = 'root'
        else:
            module = rel_path.split(os.sep)[0]
        
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in extensions:
                file_path = os.path.join(root, file)
                total, code, comment, blank = count_lines(file_path)
                
                stats[module]['files'] += 1
                stats[module]['total'] += total
                stats[module]['code'] += code
                stats[module]['comment'] += comment
                stats[module]['blank'] += blank
    
    return stats

def generate_report():
    """生成报告"""
    print("=" * 80)
    print("医药价格发现系统 - 代码统计报告")
    print("=" * 80)
    
    # Python文件统计
    print("\n## Python代码统计\n")
    py_stats = analyze_directory('.', ['.py'])
    
    print(f"{'模块':<20} {'文件数':>8} {'总行数':>10} {'代码行':>10} {'注释行':>10} {'空行':>10}")
    print("-" * 80)
    
    total_stats = {'files': 0, 'total': 0, 'code': 0, 'comment': 0, 'blank': 0}
    
    for module in sorted(py_stats.keys()):
        stats = py_stats[module]
        print(f"{module:<20} {stats['files']:>8} {stats['total']:>10} {stats['code']:>10} {stats['comment']:>10} {stats['blank']:>10}")
        for key in total_stats:
            total_stats[key] += stats[key]
    
    print("-" * 80)
    print(f"{'总计':<20} {total_stats['files']:>8} {total_stats['total']:>10} {total_stats['code']:>10} {total_stats['comment']:>10} {total_stats['blank']:>10}")
    
    # HTML文件统计
    print("\n## HTML模板统计\n")
    html_stats = analyze_directory('.', ['.html'])
    
    html_total = sum(s['total'] for s in html_stats.values())
    html_files = sum(s['files'] for s in html_stats.values())
    
    print(f"HTML文件数: {html_files}")
    print(f"总行数: {html_total}")
    
    # Markdown文件统计
    print("\n## 文档统计\n")
    md_stats = analyze_directory('.', ['.md'])
    
    md_total = sum(s['total'] for s in md_stats.values())
    md_files = sum(s['files'] for s in md_stats.values())
    
    print(f"Markdown文件数: {md_files}")
    print(f"总行数: {md_total}")
    
    # 总计
    print("\n## 项目总计\n")
    print(f"Python文件: {total_stats['files']}个, {total_stats['total']}行")
    print(f"HTML文件: {html_files}个, {html_total}行")
    print(f"Markdown文件: {md_files}个, {md_total}行")
    print(f"总计: {total_stats['files'] + html_files + md_files}个文件, {total_stats['total'] + html_total + md_total}行")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    generate_report()
