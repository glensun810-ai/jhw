"""
Source Weight Library for GEO Content Quality Validator
Implements a database of website influence weights and domain matching logic
"""
import sqlite3
import re
from urllib.parse import urlparse
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import os
from .logging_config import db_logger


class SourceWeightLibrary:
    """
    Database of website influence weights for evaluating AI response sources
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize the source weight library
        
        Args:
            db_path: Path to SQLite database file. If None, uses default location
        """
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database.db')
        
        self.db_path = db_path
        self.init_database()
        self.load_default_weights()
        
        db_logger.info(f"SourceWeightLibrary initialized with database: {db_path}")
    
    def init_database(self):
        """
        Initialize the database with sources table
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create sources table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE NOT NULL,
                site_name TEXT NOT NULL,
                weight_score REAL CHECK(weight_score >= 0 AND weight_score <= 1.0) NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for faster lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_domain ON sources(domain)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON sources(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_weight ON sources(weight_score)')
        
        conn.commit()
        conn.close()
        
        db_logger.info("Sources table created or verified")
    
    def load_default_weights(self):
        """
        Load default source weights into the database
        """
        default_sources = [
            # Official websites and authoritative sources
            ('baidu.com', '百度', 0.95, '权威媒体', '中国最大搜索引擎，权威性高'),
            ('baike.baidu.com', '百度百科', 1.0, '官方', '权威知识库'),
            ('zhihu.com', '知乎', 0.8, '权威媒体', '专业问答社区'),
            ('weibo.com', '微博', 0.7, '社交媒体', '社交媒体平台'),
            ('xiaohongshu.com', '小红书', 0.7, '社交媒体', '生活方式分享平台'),
            ('doubao.com', '豆包', 0.6, 'AI平台', '字节跳动AI助手'),
            ('qwen.com', '通义千问', 0.6, 'AI平台', '阿里通义千问'),
            ('wenxin.baidu.com', '文心一言', 0.6, 'AI平台', '百度文心一言'),
            ('deepseek.com', 'DeepSeek', 0.6, 'AI平台', 'DeepSeek AI平台'),
            ('kimi.moonshot.com', 'Kimi', 0.6, 'AI平台', '月之暗面Kimi'),
            
            # News portals
            ('news.sina.com.cn', '新浪新闻', 0.9, '权威媒体', '主流新闻门户'),
            ('news.163.com', '网易新闻', 0.9, '权威媒体', '主流新闻门户'),
            ('news.qq.com', '腾讯新闻', 0.9, '权威媒体', '主流新闻门户'),
            ('people.com.cn', '人民网', 0.95, '权威媒体', '官方新闻网站'),
            ('xinhuanet.com', '新华网', 0.95, '权威媒体', '官方新闻网站'),
            
            # Social media and community sites
            ('tieba.baidu.com', '百度贴吧', 0.5, '社交媒体', '社区讨论平台'),
            ('douban.com', '豆瓣', 0.6, '社交媒体', '文化生活社区'),
            ('bilibili.com', 'B站', 0.6, '社交媒体', '视频分享社区'),
            
            # E-commerce and business sites
            ('taobao.com', '淘宝', 0.6, '电商平台', '电商购物平台'),
            ('jd.com', '京东', 0.6, '电商平台', '电商购物平台'),
            ('tmall.com', '天猫', 0.6, '电商平台', '电商购物平台'),
            
            # Technology and developer sites
            ('github.com', 'GitHub', 0.8, '技术社区', '代码托管平台'),
            ('stackoverflow.com', 'Stack Overflow', 0.85, '技术社区', '程序员问答社区'),
            ('csdn.net', 'CSDN', 0.7, '技术社区', 'IT技术社区'),
            
            # Potential negative sources (lower weights)
            ('example-blacklist.com', '示例黑名单', 0.1, '黑灰产', '示例负面来源'),
            ('spam-site.com', '垃圾站点', 0.05, '黑灰产', '垃圾信息站点'),
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for domain, site_name, weight_score, category, description in default_sources:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO sources 
                    (domain, site_name, weight_score, category, description) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (domain, site_name, weight_score, category, description))
            except sqlite3.Error as e:
                db_logger.error(f"Error inserting source {domain}: {e}")
        
        conn.commit()
        conn.close()
        
        db_logger.info(f"Loaded {len(default_sources)} default source weights")
    
    def get_source_weight(self, domain: str) -> Optional[Tuple[float, str, str]]:
        """
        Get the weight score for a specific domain
        
        Args:
            domain: Domain name to look up
            
        Returns:
            Tuple of (weight_score, site_name, category) or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT weight_score, site_name, category 
            FROM sources 
            WHERE domain = ?
        ''', (domain,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result
    
    def get_multiple_source_weights(self, domains: List[str]) -> Dict[str, Optional[Tuple[float, str, str]]]:
        """
        Get weight scores for multiple domains
        
        Args:
            domains: List of domain names to look up
            
        Returns:
            Dictionary mapping domain to (weight_score, site_name, category) or None
        """
        if not domains:
            return {}
        
        # Create placeholders for SQL query
        placeholders = ','.join(['?' for _ in domains])
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT domain, weight_score, site_name, category 
            FROM sources 
            WHERE domain IN ({placeholders})
        ''', domains)
        
        results = cursor.fetchall()
        conn.close()
        
        # Create result dictionary
        result_dict = {domain: None for domain in domains}
        for domain, weight_score, site_name, category in results:
            result_dict[domain] = (weight_score, site_name, category)
        
        return result_dict
    
    def extract_domain_from_url(self, url: str) -> Optional[str]:
        """
        Extract domain from a URL
        
        Args:
            url: URL string to extract domain from
            
        Returns:
            Domain string or None if invalid
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove 'www.' prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Validate domain format
            if re.match(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$', domain):
                return domain
            else:
                return None
        except Exception:
            return None
    
    def extract_domains_from_urls(self, urls: List[str]) -> List[str]:
        """
        Extract domains from a list of URLs
        
        Args:
            urls: List of URL strings
            
        Returns:
            List of extracted domain strings
        """
        domains = []
        for url in urls:
            domain = self.extract_domain_from_url(url)
            if domain:
                domains.append(domain)
        
        return list(set(domains))  # Remove duplicates
    
    def get_sources_by_category(self, category: str) -> List[Dict[str, any]]:
        """
        Get all sources in a specific category
        
        Args:
            category: Category to filter by
            
        Returns:
            List of source dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT domain, site_name, weight_score, category, description, created_at, updated_at
            FROM sources 
            WHERE category = ?
            ORDER BY weight_score DESC
        ''', (category,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'domain': row[0],
                'site_name': row[1],
                'weight_score': row[2],
                'category': row[3],
                'description': row[4],
                'created_at': row[5],
                'updated_at': row[6]
            }
            for row in results
        ]
    
    def get_high_weight_sources(self, min_weight: float = 0.7) -> List[Dict[str, any]]:
        """
        Get sources with weight above threshold

        Args:
            min_weight: Minimum weight threshold

        Returns:
            List of high-weight source dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT domain, site_name, weight_score, category, description, created_at, updated_at
            FROM sources
            WHERE weight_score >= ?
            ORDER BY weight_score DESC
        ''', (min_weight,))

        results = cursor.fetchall()
        conn.close()

        return [
            {
                'domain': row[0],
                'site_name': row[1],
                'weight_score': row[2],
                'category': row[3],
                'description': row[4],
                'created_at': row[5],
                'updated_at': row[6]
            }
            for row in results
        ]

    def extract_domain_from_url(self, url: str) -> Optional[str]:
        """
        Extract domain from a URL

        Args:
            url: URL string to extract domain from

        Returns:
            Domain string or None if invalid
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove 'www.' prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]

            # Validate domain format
            if re.match(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$', domain):
                return domain
            else:
                return None
        except Exception:
            return None

    def add_source(self, domain: str, site_name: str, weight_score: float, category: str, description: str = ""):
        """
        Add a new source to the database

        Args:
            domain: Domain name
            site_name: Site name
            weight_score: Weight score (0-1.0)
            category: Category
            description: Description of the source
        """
        if not (0 <= weight_score <= 1.0):
            raise ValueError("Weight score must be between 0 and 1.0")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO sources
                (domain, site_name, weight_score, category, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (domain, site_name, weight_score, category, description))

            conn.commit()
            db_logger.info(f"Added new source: {domain} with weight {weight_score}")
        except sqlite3.IntegrityError:
            db_logger.warning(f"Source already exists: {domain}")
        finally:
            conn.close()
    
    def update_source_weight(self, domain: str, new_weight: float):
        """
        Update the weight of an existing source

        Args:
            domain: Domain name to update
            new_weight: New weight score (0-1.0)
        """
        if not (0 <= new_weight <= 1.0):
            raise ValueError("Weight score must be between 0 and 1.0")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE sources
            SET weight_score = ?, updated_at = CURRENT_TIMESTAMP
            WHERE domain = ?
        ''', (new_weight, domain))

        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        if rows_affected > 0:
            db_logger.info(f"Updated weight for {domain} to {new_weight}")
        else:
            db_logger.warning(f"No source found for domain: {domain}")

    def get_all_categories(self) -> List[str]:
        """
        Get all available source categories

        Returns:
            List of all categories in the database
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT DISTINCT category FROM sources ORDER BY category')
        categories = [row[0] for row in cursor.fetchall()]

        conn.close()
        return categories

    def get_all_sources(self) -> List[Dict[str, any]]:
        """
        Get all sources from the database

        Returns:
            List of all source dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT domain, site_name, weight_score, category, description, created_at, updated_at
            FROM sources
            ORDER BY weight_score DESC
        ''')

        results = cursor.fetchall()
        conn.close()

        return [
            {
                'domain': row[0],
                'site_name': row[1],
                'weight_score': row[2],
                'category': row[3],
                'description': row[4],
                'created_at': row[5],
                'updated_at': row[6]
            }
            for row in results
        ]

    def search_sources_by_domain(self, domain_pattern: str) -> List[Dict[str, any]]:
        """
        Search sources by domain pattern

        Args:
            domain_pattern: Pattern to search for in domains

        Returns:
            List of matching source dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT domain, site_name, weight_score, category, description, created_at, updated_at
            FROM sources
            WHERE domain LIKE ?
            ORDER BY weight_score DESC
        ''', (f'%{domain_pattern}%',))

        results = cursor.fetchall()
        conn.close()

        return [
            {
                'domain': row[0],
                'site_name': row[1],
                'weight_score': row[2],
                'category': row[3],
                'description': row[4],
                'created_at': row[5],
                'updated_at': row[6]
            }
            for row in results
        ]

    def get_sources_by_weights_range(self, min_weight: float, max_weight: float) -> List[Dict[str, any]]:
        """
        Get sources within a specific weight range

        Args:
            min_weight: Minimum weight threshold
            max_weight: Maximum weight threshold

        Returns:
            List of sources within the weight range
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT domain, site_name, weight_score, category, description, created_at, updated_at
            FROM sources
            WHERE weight_score BETWEEN ? AND ?
            ORDER BY weight_score DESC
        ''', (min_weight, max_weight))

        results = cursor.fetchall()
        conn.close()

        return [
            {
                'domain': row[0],
                'site_name': row[1],
                'weight_score': row[2],
                'category': row[3],
                'description': row[4],
                'created_at': row[5],
                'updated_at': row[6]
            }
            for row in results
        ]


# Example usage
if __name__ == "__main__":
    # Initialize the source weight library
    swl = SourceWeightLibrary()
    
    # Test domain extraction
    test_urls = [
        "https://www.baidu.com/some/page",
        "http://zhihu.com/question/123",
        "https://news.qq.com/article/abc"
    ]
    
    domains = swl.extract_domains_from_urls(test_urls)
    print(f"Extracted domains: {domains}")
    
    # Test weight lookup
    for domain in domains:
        weight_info = swl.get_source_weight(domain)
        if weight_info:
            weight, site_name, category = weight_info
            print(f"Domain: {domain}, Weight: {weight}, Site: {site_name}, Category: {category}")
        else:
            print(f"Domain: {domain}, Weight: Not found")
    
    # Test high-weight sources
    high_weight_sources = swl.get_high_weight_sources(min_weight=0.8)
    print(f"\nHigh weight sources (>= 0.8): {len(high_weight_sources)}")
    for source in high_weight_sources[:5]:  # Show first 5
        print(f"  {source['site_name']} ({source['domain']}): {source['weight_score']}")