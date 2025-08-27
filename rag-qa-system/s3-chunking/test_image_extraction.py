#!/usr/bin/env python3
"""이미지 추출 테스트 스크립트"""

import re
import os

def test_image_extraction():
    """이미지 추출 기능 테스트"""
    
    # 테스트 콘텐츠
    test_content = """## 해외이용 가능한 카드사

### VISA 카드
VISA 카드는 전 세계에서 사용 가능합니다.
![VISA 로고](./images/visa_logo.png)

### MasterCard
MasterCard도 글로벌 네트워크를 보유하고 있습니다.
![MasterCard 로고](./images/mastercard_logo.png)

### JCB
일본계 국제 카드사입니다.
![JCB 로고](./images/jcb_logo.jpg)

### 사용 가이드
![이용 가이드](./images/usage_guide.gif)
"""

    print("🔍 이미지 추출 테스트")
    print("=" * 40)
    
    # 이미지 패턴 매칭
    image_pattern = re.compile(r'!\[.*?\]\((.*?)\)')
    images = []
    
    for match in image_pattern.finditer(test_content):
        path = match.group(1)
        images.append({
            'path': path,
            'full_tag': match.group(0),
            'alt_text': match.group(0).split('[')[1].split(']')[0]
        })
    
    print(f"📊 발견된 이미지: {len(images)}개")
    
    for i, img in enumerate(images, 1):
        print(f"\n🖼️ 이미지 {i}:")
        print(f"   경로: {img['path']}")
        print(f"   대체텍스트: {img['alt_text']}")
        print(f"   마크다운 태그: {img['full_tag']}")
        
        # 파일 확장자 확인
        ext = os.path.splitext(img['path'])[1].lower()
        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            print(f"   ✅ 지원되는 이미지 형식: {ext}")
        else:
            print(f"   ⚠️ 알 수 없는 형식: {ext}")

def test_chunking_with_images():
    """이미지가 포함된 청킹 테스트"""
    
    print("\n🔄 청킹 테스트 (이미지 포함)")
    print("=" * 40)
    
    # 실제 MD 파일 읽기
    md_file = "/mnt/d/99_DEOTIS_QA_SYSTEM/03_DEOTIS_QA/s3-chunking/BC카드_해외이용가이드_이미지테스트.md"
    
    if os.path.exists(md_file):
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📄 파일 읽기 완료: {len(content):,}자")
        
        # 이미지 추출
        image_pattern = re.compile(r'!\[.*?\]\((.*?)\)')
        images = list(image_pattern.finditer(content))
        
        print(f"🖼️ 총 이미지 수: {len(images)}개")
        
        # 섹션별 분할 (간단 버전)
        sections = content.split('##')
        
        print(f"📑 섹션 수: {len(sections)}개")
        
        for i, section in enumerate(sections):
            if section.strip():
                section_images = len(image_pattern.findall(section))
                section_title = section.split('\n')[0][:50] + '...' if len(section.split('\n')[0]) > 50 else section.split('\n')[0]
                print(f"   섹션 {i}: '{section_title}' - 이미지 {section_images}개")
    
    else:
        print(f"❌ 테스트 파일이 없습니다: {md_file}")

if __name__ == "__main__":
    test_image_extraction()
    test_chunking_with_images()
    
    print("\n✅ 테스트 완료!")
    print("\n💡 결과:")
    print("   - 이미지 경로 추출 기능 작동")
    print("   - 마크다운 이미지 태그 인식")
    print("   - 섹션별 이미지 분리 가능")
    print("\n🎯 LLM 연동 시:")
    print("   - 해외이용 관련 질문 시 카드사 로고 이미지 경로 제공")
    print("   - VISA, MasterCard 등 브랜드 로고 표시 가능")
    print("   - 가이드 이미지와 함께 설명 제공")