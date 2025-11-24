"""
Unknown Fall Descriptions 단어 빈도 분석
"""

import re
from collections import Counter
from typing import List, Tuple

def extract_descriptions(filename: str) -> List[str]:
    """텍스트 파일에서 Description 부분만 추출"""
    descriptions = []
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Description: 부터 다음 섹션까지 추출
    pattern = r'Description:\n-{80}\n(.*?)\n\nProgress Notes:'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for match in matches:
        descriptions.append(match.strip())
    
    return descriptions

def analyze_word_frequency(descriptions: List[str], top_n: int = 20) -> List[Tuple[str, int]]:
    """단어 빈도 분석"""
    
    # 불용어 (의미 없는 단어들)
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'were', 'been', 'be',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them', 'their', 'his',
        'her', 'its', 'our', 'your', 'my', 'me', 'him',
        'am', 'are', 'there', 'where', 'when', 'how', 'what', 'which', 'who',
        'not', 'no', 'yes', 'all', 'any', 'some', 'few', 'more', 'most',
        'other', 'such', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
        'just', 'also', 'into', 'through', 'during', 'before', 'after',
        'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under',
        'again', 'further', 'then', 'once', 'here', 'both', 'each',
        'about', 'against', 'between', 'because', 'while', 'since',
        's', 't', 'd', 'm', 'll', 've', 're', 'description', 'no'
    }
    
    all_words = []
    
    for desc in descriptions:
        # 소문자로 변환
        desc_lower = desc.lower()
        
        # 단어 추출 (알파벳만)
        words = re.findall(r'\b[a-z]+\b', desc_lower)
        
        # 불용어 제거 및 2글자 이상만
        filtered_words = [
            word for word in words 
            if word not in stop_words and len(word) >= 2
        ]
        
        all_words.extend(filtered_words)
    
    # 빈도 계산
    word_counts = Counter(all_words)
    
    return word_counts.most_common(top_n)

def main():
    filename = 'unknown_falls_20251124_150957.txt'
    
    print("🔍 Unknown Falls Description 단어 빈도 분석\n")
    print("=" * 80)
    
    # Description 추출
    descriptions = extract_descriptions(filename)
    print(f"✅ {len(descriptions)}개의 Description 추출 완료\n")
    
    # 단어 빈도 분석
    top_words = analyze_word_frequency(descriptions, top_n=20)
    
    print("📊 상위 20개 빈출 단어:\n")
    print(f"{'순위':<5} {'단어':<20} {'빈도':<10} {'비율':<10}")
    print("-" * 80)
    
    total_words = sum(count for _, count in top_words)
    
    for rank, (word, count) in enumerate(top_words, 1):
        percentage = (count / total_words * 100) if total_words > 0 else 0
        print(f"{rank:<5} {word:<20} {count:<10} {percentage:>6.1f}%")
    
    print("\n" + "=" * 80)
    
    # 통계 정보
    all_words_count = sum(count for _, count in analyze_word_frequency(descriptions, top_n=10000))
    unique_words = len(set(word for desc in descriptions for word in re.findall(r'\b[a-z]+\b', desc.lower())))
    
    print(f"\n📈 통계:")
    print(f"  - 총 단어 수 (불용어 제외): {all_words_count:,}")
    print(f"  - 고유 단어 수: {unique_words:,}")
    print(f"  - 평균 Description 길이: {all_words_count / len(descriptions):.1f} 단어")
    
    # Witnessed/Unwitnessed 관련 키워드 확인
    print(f"\n🔍 Fall 유형 관련 키워드 출현 빈도:")
    print("-" * 80)
    
    keywords = {
        'witnessed': ['witnessed', 'witness', 'staff', 'seen', 'observed', 'watching', 'present'],
        'unwitnessed': ['unwitnessed', 'found', 'discovered', 'lying', 'floor', 'ground', 'alone', 'unattended']
    }
    
    combined_text = ' '.join(descriptions).lower()
    
    print("\n[Witnessed 관련 키워드]")
    for keyword in keywords['witnessed']:
        count = combined_text.count(keyword)
        if count > 0:
            print(f"  - {keyword}: {count}회")
    
    print("\n[Unwitnessed 관련 키워드]")
    for keyword in keywords['unwitnessed']:
        count = combined_text.count(keyword)
        if count > 0:
            print(f"  - {keyword}: {count}회")
    
    print("\n💡 새로운 패턴 찾기 도움말:")
    print("  1. 상위 빈출 단어 중 Fall 유형과 관련 있는 단어를 찾아보세요")
    print("  2. 'found', 'discovered' 등은 Unwitnessed의 강력한 지표입니다")
    print("  3. 'staff', 'witness' 등은 Witnessed의 강력한 지표입니다")
    
    # 샘플 Description 출력 (처음 3개)
    print("\n" + "=" * 80)
    print("📄 샘플 Descriptions (처음 3개):\n")
    for idx, desc in enumerate(descriptions[:3], 1):
        print(f"[{idx}] {desc[:200]}..." if len(desc) > 200 else f"[{idx}] {desc}")
        print("-" * 80)

if __name__ == '__main__':
    main()

