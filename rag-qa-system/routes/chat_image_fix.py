# 청킹 타입별 이미지 처리 분기 코드
def generate_card_images_by_chunking_type(analysis, detected_user, process_id, chunking_type):
    """청킹 타입에 따른 조건부 이미지 처리"""
    
    owned_card_images = []
    available_card_images = []
    process_image = ""
    
    # s3-chunking (custom)만 이미지 포함
    if chunking_type == "custom":
        print(f"🖼️ [vLLM {process_id}] s3-chunking: 이미지 포함 모드")
        # 동적 카드 분석 서비스 사용 (벡터DB에서 이미지 추출)
        from services.card_analysis_service_new import DynamicCardAnalysisService
        dynamic_service = DynamicCardAnalysisService()
        dynamic_analysis = dynamic_service.analyze_customer_cards(detected_user, "custom")
        
        # 보유 카드 이미지
        for card in dynamic_analysis.owned_cards:
            if card.image_path:
                owned_card_images.append(f'![{card.name}](/images/{card.image_path})')
        
        # 발급 가능/추천 카드 이미지
        for card in dynamic_analysis.available_cards + dynamic_analysis.recommended_cards:
            if card.image_path:
                available_card_images.append(f'![{card.name}](/images/{card.image_path})')
        
        # 카드 발급 절차 이미지 (벡터DB에서 찾으면 포함)
        process_image = '![카드발급 절차](/images/Aspose.Words.4c2a2064-0c7c-48d5-aca6-c4d7a6eade2b.013.gif)'
        
    else:  # s3 (basic) - 텍스트만
        print(f"📝 [vLLM {process_id}] s3기본: 텍스트 전용 모드 (이미지 없음)")
        # 이미지 없이 텍스트만 처리 - 빈 배열 유지
        
    return owned_card_images, available_card_images, process_image


# chat.py의 948-973 라인 교체용 코드
replacement_code = '''
                            # 청킹 타입별 이미지 처리 분기
                            owned_card_images = []
                            available_card_images = []
                            process_image = ""
                            
                            # s3-chunking (custom)만 이미지 포함
                            if chunking_type == "custom":
                                print(f"🖼️ [vLLM {process_id}] s3-chunking: 이미지 포함 모드")
                                # 동적 카드 분석 서비스 사용 (벡터DB에서 이미지 추출)
                                from services.card_analysis_service_new import DynamicCardAnalysisService
                                dynamic_service = DynamicCardAnalysisService()
                                dynamic_analysis = dynamic_service.analyze_customer_cards(detected_user, "custom")
                                
                                # 보유 카드 이미지
                                for card in dynamic_analysis.owned_cards:
                                    if card.image_path:
                                        owned_card_images.append(f'![{card.name}](/images/{card.image_path})')
                                
                                # 발급 가능/추천 카드 이미지
                                for card in dynamic_analysis.available_cards + dynamic_analysis.recommended_cards:
                                    if card.image_path:
                                        available_card_images.append(f'![{card.name}](/images/{card.image_path})')
                                
                                # 카드 발급 절차 이미지 (벡터DB에서 찾으면 포함)
                                process_image = '![카드발급 절차](/images/Aspose.Words.4c2a2064-0c7c-48d5-aca6-c4d7a6eade2b.013.gif)'
                                
                            else:  # s3 (basic) - 텍스트만
                                print(f"📝 [vLLM {process_id}] s3기본: 텍스트 전용 모드 (이미지 없음)")
                                # 이미지 없이 텍스트만 처리
'''

print("청킹 타입별 이미지 처리 코드 준비 완료!")