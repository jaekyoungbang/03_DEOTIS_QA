#!/usr/bin/env python3
"""
청킹 전략 비교 테스트 스크립트
- 다양한 청킹 전략의 효과 비교
- 질문별 유사도 측정 및 분석
"""

import os
import sys
import time
from typing import Dict, List, Tuple
import json

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.embeddings import EmbeddingManager
from models.vectorstore import DualVectorStoreManager
from services.advanced_chunking_strategies import AdvancedChunkingStrategies
from load_s3_chunking_md import S3ChunkingMDLoader

class ChunkingStrategyTester:
    """청킹 전략 테스트 클래스"""
    
    def __init__(self):
        self.embedding_manager = EmbeddingManager()
        self.vectorstore_manager = DualVectorStoreManager(self.embedding_manager.get_embeddings())
        
        # BC카드 관련 테스트 질문들 (카테고리별)
        self.test_questions = {
            "개인화 카드 정보": [
                "김명정님이 현재 보유하고 있는 카드는 무엇인가요?",
                "김명정님이 새로 발급받을 수 있는 카드를 알려주세요",
                "김명정님의 카드 보유 현황을 확인해주세요",
                "김명정님이 추가로 신청 가능한 카드는 어떤 것들이 있나요?"
            ],
            "카드 발급": [
                "BC카드 발급 방법이 어떻게 되나요?",
                "신용카드 신청 절차를 알려주세요",
                "BC카드 발급에 필요한 서류는 무엇인가요?",
                "카드 발급 심사 기준은 어떻게 되나요?"
            ],
            "고객 서비스": [
                "민원 접수는 어떻게 하나요?",
                "BC카드 고객센터 연락처를 알려주세요",
                "서면 접수 방법이 궁금합니다",
                "전화로 문의하려면 어디로 연락해야 하나요?"
            ],
            "결제 및 수수료": [
                "결제일별 신용공여기간은 어떻게 되나요?",
                "1일 결제일의 신용공여기간을 알려주세요",
                "할부수수료율은 얼마인가요?",
                "연회비 정보를 알고 싶습니다"
            ],
            "장애인 지원": [
                "장애유형별 본인확인 방법은 어떻게 되나요?",
                "시각장애인을 위한 서비스가 있나요?",
                "청각장애인 고객 지원 방법을 알려주세요",
                "신체장애인 카드 신청 방법은 어떻게 되나요?"
            ]
        }
        
        # 청킹 전략 목록
        self.strategies = ["semantic", "question_aware", "hierarchical", "hybrid"]
        
    def load_data_with_strategy(self, strategy: str) -> bool:
        """특정 전략으로 데이터 로드"""
        print(f"\n🔄 {strategy} 전략으로 데이터 로딩 중...")
        
        try:
            # 기존 데이터 클리어
            self.vectorstore_manager.clear_collection("custom")
            time.sleep(1)
            
            # 새 전략으로 로드
            loader = S3ChunkingMDLoader(
                use_advanced_chunking=strategy != "legacy",
                default_chunking_strategy=strategy
            )
            
            # 조용한 로딩을 위해 출력 억제
            import io
            from contextlib import redirect_stdout
            
            with redirect_stdout(io.StringIO()):
                loader.load_s3_chunking_md_files(
                    clear_before_load=False,
                    chunking_strategy=strategy
                )
            
            print(f"✅ {strategy} 전략 로딩 완료")
            return True
            
        except Exception as e:
            print(f"❌ {strategy} 전략 로딩 실패: {e}")
            return False
    
    def test_strategy_performance(self, strategy: str) -> Dict:
        """전략별 성능 테스트"""
        print(f"\n🧪 {strategy} 전략 테스트 중...")
        
        results = {
            "strategy": strategy,
            "category_results": {},
            "overall_stats": {
                "total_questions": 0,
                "avg_similarity": 0.0,
                "high_quality_responses": 0,  # 80% 이상
                "medium_quality_responses": 0,  # 60-80%
                "low_quality_responses": 0     # 60% 미만
            }
        }
        
        all_similarities = []
        
        # 카테고리별 테스트
        for category, questions in self.test_questions.items():
            print(f"  📋 {category} 테스트...")
            category_similarities = []
            
            for question in questions:
                try:
                    # 유사도 검색
                    search_results = self.vectorstore_manager.similarity_search_with_score(
                        question, "custom", k=3
                    )
                    
                    if search_results:
                        # 최고 유사도 점수 가져오기
                        top_similarity = 1.0 - search_results[0][1]  # distance to similarity
                        category_similarities.append(top_similarity)
                        all_similarities.append(top_similarity)
                        
                        # 품질 분류
                        if top_similarity >= 0.8:
                            results["overall_stats"]["high_quality_responses"] += 1
                        elif top_similarity >= 0.6:
                            results["overall_stats"]["medium_quality_responses"] += 1
                        else:
                            results["overall_stats"]["low_quality_responses"] += 1
                    else:
                        category_similarities.append(0.0)
                        all_similarities.append(0.0)
                        results["overall_stats"]["low_quality_responses"] += 1
                        
                except Exception as e:
                    print(f"    ⚠️ 질문 테스트 실패: {question[:30]}... - {e}")
                    category_similarities.append(0.0)
                    all_similarities.append(0.0)
                    results["overall_stats"]["low_quality_responses"] += 1
            
            # 카테고리 결과 저장
            if category_similarities:
                avg_category_similarity = sum(category_similarities) / len(category_similarities)
                results["category_results"][category] = {
                    "avg_similarity": avg_category_similarity,
                    "question_count": len(category_similarities),
                    "similarities": category_similarities
                }
                print(f"    ✅ 평균 유사도: {avg_category_similarity:.1%}")
            else:
                results["category_results"][category] = {
                    "avg_similarity": 0.0,
                    "question_count": 0,
                    "similarities": []
                }
        
        # 전체 통계 계산
        if all_similarities:
            results["overall_stats"]["total_questions"] = len(all_similarities)
            results["overall_stats"]["avg_similarity"] = sum(all_similarities) / len(all_similarities)
        
        return results
    
    def compare_all_strategies(self) -> Dict:
        """모든 전략 비교"""
        print("🔍 청킹 전략 성능 비교 테스트 시작")
        print("=" * 60)
        
        all_results = {}
        
        for strategy in self.strategies:
            # 데이터 로드
            if self.load_data_with_strategy(strategy):
                # 성능 테스트
                results = self.test_strategy_performance(strategy)
                all_results[strategy] = results
                
                # 간단한 결과 출력
                avg_sim = results["overall_stats"]["avg_similarity"]
                high_q = results["overall_stats"]["high_quality_responses"]
                total_q = results["overall_stats"]["total_questions"]
                
                print(f"  📊 전체 평균 유사도: {avg_sim:.1%}")
                print(f"  🎯 고품질 응답: {high_q}/{total_q} ({high_q/total_q*100:.1f}%)")
        
        return all_results
    
    def generate_comparison_report(self, results: Dict) -> str:
        """비교 리포트 생성"""
        report = []
        report.append("📊 청킹 전략 성능 비교 리포트")
        report.append("=" * 50)
        
        # 전략별 요약
        strategy_scores = {}
        for strategy, data in results.items():
            if data:
                avg_sim = data["overall_stats"]["avg_similarity"]
                high_quality_rate = data["overall_stats"]["high_quality_responses"] / max(data["overall_stats"]["total_questions"], 1)
                strategy_scores[strategy] = {
                    "avg_similarity": avg_sim,
                    "high_quality_rate": high_quality_rate,
                    "combined_score": (avg_sim * 0.7) + (high_quality_rate * 0.3)  # 가중 점수
                }
        
        # 순위별 정렬
        sorted_strategies = sorted(strategy_scores.items(), key=lambda x: x[1]["combined_score"], reverse=True)
        
        report.append("\n🏆 종합 순위:")
        for rank, (strategy, scores) in enumerate(sorted_strategies, 1):
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "📋"
            report.append(f"{medal} {rank}위: {strategy}")
            report.append(f"   평균 유사도: {scores['avg_similarity']:.1%}")
            report.append(f"   고품질 응답률: {scores['high_quality_rate']:.1%}")
            report.append(f"   종합 점수: {scores['combined_score']:.3f}")
        
        # 카테고리별 최고 성능
        report.append("\n📋 카테고리별 최고 성능:")
        categories = set()
        for data in results.values():
            if data:
                categories.update(data["category_results"].keys())
        
        for category in categories:
            best_strategy = None
            best_score = 0.0
            
            for strategy, data in results.items():
                if data and category in data["category_results"]:
                    score = data["category_results"][category]["avg_similarity"]
                    if score > best_score:
                        best_score = score
                        best_strategy = strategy
            
            if best_strategy:
                report.append(f"  🎯 {category}: {best_strategy} ({best_score:.1%})")
        
        # 세부 분석
        report.append("\n📈 세부 분석:")
        for strategy, data in results.items():
            if not data:
                continue
                
            report.append(f"\n🔹 {strategy.upper()} 전략:")
            stats = data["overall_stats"]
            report.append(f"  전체 질문 수: {stats['total_questions']}개")
            report.append(f"  평균 유사도: {stats['avg_similarity']:.1%}")
            report.append(f"  고품질 응답: {stats['high_quality_responses']}개 ({stats['high_quality_responses']/stats['total_questions']*100:.1f}%)")
            report.append(f"  중품질 응답: {stats['medium_quality_responses']}개 ({stats['medium_quality_responses']/stats['total_questions']*100:.1f}%)")
            report.append(f"  저품질 응답: {stats['low_quality_responses']}개 ({stats['low_quality_responses']/stats['total_questions']*100:.1f}%)")
            
            # 카테고리별 성능
            report.append("  카테고리별 성능:")
            for category, cat_data in data["category_results"].items():
                report.append(f"    - {category}: {cat_data['avg_similarity']:.1%}")
        
        # 권장사항
        report.append("\n💡 권장사항:")
        if sorted_strategies:
            best_strategy = sorted_strategies[0][0]
            best_score = sorted_strategies[0][1]["combined_score"]
            
            report.append(f"  🌟 가장 우수한 성능: {best_strategy}")
            report.append(f"  🎯 종합 점수: {best_score:.3f}")
            
            if best_strategy == "hybrid":
                report.append("  📋 하이브리드 전략이 최고 성능을 보입니다.")
                report.append("      여러 청킹 방법을 조합하여 균형잡힌 결과를 제공합니다.")
            elif best_strategy == "semantic":
                report.append("  📋 의미론적 청킹이 최고 성능을 보입니다.")
                report.append("      문맥과 의미를 중시하는 질문에 특히 효과적입니다.")
            elif best_strategy == "question_aware":
                report.append("  📋 질문 유형별 청킹이 최고 성능을 보입니다.")
                report.append("      특정 질문 패턴에 최적화된 응답을 제공합니다.")
            elif best_strategy == "hierarchical":
                report.append("  📋 계층적 청킹이 최고 성능을 보입니다.")
                report.append("      문서 구조를 잘 활용하여 체계적인 응답을 제공합니다.")
        
        return "\n".join(report)
    
    def save_detailed_results(self, results: Dict, filename: str = "chunking_strategy_comparison.json"):
        """상세 결과를 JSON으로 저장"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n💾 상세 결과가 {filename}에 저장되었습니다.")
        except Exception as e:
            print(f"❌ 결과 저장 실패: {e}")

def main():
    """메인 실행 함수"""
    tester = ChunkingStrategyTester()
    
    # 전략 비교 실행
    results = tester.compare_all_strategies()
    
    # 리포트 생성 및 출력
    report = tester.generate_comparison_report(results)
    print("\n" + report)
    
    # 결과 저장
    tester.save_detailed_results(results)
    
    print("\n🎉 청킹 전략 비교 테스트 완료!")

if __name__ == "__main__":
    main()