import React, { useEffect, useRef } from 'react';
import { GazeResultProps } from './types';

const VideoGazeResult: React.FC<GazeResultProps> = ({ result, onRestart }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // 시선 궤적 시각화
  useEffect(() => {
    if (!canvasRef.current || !result.gaze_points || result.gaze_points.length === 0) {
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 캔버스 크기 설정
    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;

    // 캔버스 초기화
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);

    // 좌표 정규화를 위한 범위 계산
    const xCoords = result.gaze_points.map(point => point[0]);
    const yCoords = result.gaze_points.map(point => point[1]);
    
    const minX = Math.min(...xCoords);
    const maxX = Math.max(...xCoords);
    const minY = Math.min(...yCoords);
    const maxY = Math.max(...yCoords);

    // 좌표 변환 함수
    const transformX = (x: number) => {
      const normalized = (x - minX) / (maxX - minX || 1);
      return normalized * (canvasWidth - 40) + 20;
    };

    const transformY = (y: number) => {
      const normalized = (y - minY) / (maxY - minY || 1);
      return normalized * (canvasHeight - 40) + 20;
    };

    // 배경 그리기
    ctx.fillStyle = '#f9fafb';
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    // 시선 궤적 그리기
    if (result.gaze_points.length > 1) {
      ctx.strokeStyle = '#3b82f6';
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();

      const firstPoint = result.gaze_points[0];
      ctx.moveTo(transformX(firstPoint[0]), transformY(firstPoint[1]));

      for (let i = 1; i < result.gaze_points.length; i++) {
        const point = result.gaze_points[i];
        ctx.lineTo(transformX(point[0]), transformY(point[1]));
      }

      ctx.stroke();
      ctx.setLineDash([]);
    }

    // 시선 포인트들 그리기
    result.gaze_points.forEach((point, index) => {
      const x = transformX(point[0]);
      const y = transformY(point[1]);
      
      // 시간 순서에 따라 색상 변화 (파란색 → 빨간색)
      const ratio = index / (result.gaze_points.length - 1);
      const red = Math.round(255 * ratio);
      const blue = Math.round(255 * (1 - ratio));
      
      ctx.fillStyle = `rgb(${red}, 100, ${blue})`;
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, 2 * Math.PI);
      ctx.fill();
      
      // 흰색 테두리
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1;
      ctx.stroke();
    });

    // 시작점과 끝점 표시
    if (result.gaze_points.length > 0) {
      const startPoint = result.gaze_points[0];
      const endPoint = result.gaze_points[result.gaze_points.length - 1];
      
      // 시작점 (초록색)
      ctx.fillStyle = '#10b981';
      ctx.beginPath();
      ctx.arc(transformX(startPoint[0]), transformY(startPoint[1]), 6, 0, 2 * Math.PI);
      ctx.fill();
      
      // 끝점 (빨간색)
      ctx.fillStyle = '#ef4444';
      ctx.beginPath();
      ctx.arc(transformX(endPoint[0]), transformY(endPoint[1]), 6, 0, 2 * Math.PI);
      ctx.fill();
    }

    // 범례 추가
    ctx.fillStyle = '#374151';
    ctx.font = '12px Arial';
    ctx.textAlign = 'left';
    ctx.fillText('🟢 시작점', 10, canvasHeight - 30);
    ctx.fillText('🔴 끝점', 10, canvasHeight - 15);
    ctx.fillText('📈 시선 궤적', 100, canvasHeight - 30);
    ctx.fillText(`${result.gaze_points.length}개 포인트`, 100, canvasHeight - 15);

  }, [result]);

  // 점수에 따른 색상 및 메시지 결정
  const getScoreStyle = (score: number) => {
    if (score >= 85) {
      return {
        bgColor: 'bg-green-50 border-green-200',
        textColor: 'text-green-800',
        barColor: 'bg-green-500',
        emoji: '🌟'
      };
    } else if (score >= 70) {
      return {
        bgColor: 'bg-blue-50 border-blue-200',
        textColor: 'text-blue-800',
        barColor: 'bg-blue-500',
        emoji: '👍'
      };
    } else if (score >= 50) {
      return {
        bgColor: 'bg-yellow-50 border-yellow-200',
        textColor: 'text-yellow-800',
        barColor: 'bg-yellow-500',
        emoji: '⚠️'
      };
    } else {
      return {
        bgColor: 'bg-red-50 border-red-200',
        textColor: 'text-red-800',
        barColor: 'bg-red-500',
        emoji: '📈'
      };
    }
  };

  const scoreStyle = getScoreStyle(result.gaze_score);

  return (
    <div className="space-y-6">
      {/* 메인 점수 표시 */}
      <div className={`${scoreStyle.bgColor} border rounded-lg p-6 text-center`}>
        <div className="text-4xl mb-2">{scoreStyle.emoji}</div>
        <h3 className={`text-2xl font-bold ${scoreStyle.textColor} mb-2`}>
          시선 안정성 점수
        </h3>
        <div className="text-6xl font-bold text-gray-900 mb-4">
          {result.gaze_score}
        </div>
        
        {/* 점수 바 */}
        <div className="w-full bg-gray-200 rounded-full h-4 mb-4">
          <div 
            className={`${scoreStyle.barColor} h-4 rounded-full transition-all duration-1000 ease-out`}
            style={{ width: `${result.gaze_score}%` }}
          />
        </div>
        
        <div className={`${scoreStyle.textColor} font-medium text-lg`}>
          {result.stability_rating}
        </div>
      </div>

      {/* 상세 분석 결과 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-3">📊 분석 통계</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>총 프레임:</span>
              <span className="font-bold">{result.total_frames.toLocaleString()}개</span>
            </div>
            <div className="flex justify-between">
              <span>분석된 프레임:</span>
              <span className="font-bold">{result.analyzed_frames.toLocaleString()}개</span>
            </div>
            <div className="flex justify-between">
              <span>범위 내 프레임:</span>
              <span className="font-bold">{result.in_range_frames.toLocaleString()}개</span>
            </div>
            <div className="flex justify-between">
              <span>범위 준수율:</span>
              <span className="font-bold">{Math.round(result.in_range_ratio * 100)}%</span>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-3">🎯 세부 점수</h4>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>시선 흔들림 점수:</span>
                <span className="font-bold">{result.jitter_score}점</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-purple-500 h-2 rounded-full"
                  style={{ width: `${result.jitter_score}%` }}
                />
              </div>
            </div>
            
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>범위 준수 점수:</span>
                <span className="font-bold">{Math.round(result.in_range_ratio * 100)}점</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-green-500 h-2 rounded-full"
                  style={{ width: `${result.in_range_ratio * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 피드백 메시지 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-900 mb-2">💬 AI 피드백</h4>
        <p className="text-blue-800">{result.feedback}</p>
      </div>

      {/* 시선 궤적 시각화 */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-3">👁️ 시선 궤적 분석</h4>
        <p className="text-sm text-gray-600 mb-4">
          면접 중 시선의 움직임을 시각화했습니다. 파란색에서 빨간색으로 시간 순서를 나타냅니다.
        </p>
        <canvas
          ref={canvasRef}
          width={600}
          height={300}
          className="w-full border border-gray-300 rounded bg-gray-50"
        />
      </div>

      {/* 개선 팁 */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <h4 className="font-medium text-yellow-900 mb-2">💡 개선 팁</h4>
        <ul className="text-sm text-yellow-800 space-y-1">
          <li>• 면접관의 눈을 직접 바라보는 연습을 하세요</li>
          <li>• 긴장할 때 시선이 흔들리지 않도록 심호흡을 하세요</li>
          <li>• 카메라 렌즈를 면접관의 눈으로 생각하고 집중하세요</li>
          <li>• 답변 중 잠깐의 시선 이동은 자연스럽지만, 너무 자주는 피하세요</li>
          <li>• 규칙적인 아이컨택 연습으로 자신감을 기르세요</li>
        </ul>
      </div>

      {/* 분석 정보 */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-3">ℹ️ 분석 정보</h4>
        <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
          <div>
            <span className="block font-medium">분석 시간:</span>
            <span>{result.analysis_duration.toFixed(1)}초</span>
          </div>
          <div>
            <span className="block font-medium">수집된 시선 포인트:</span>
            <span>{result.gaze_points.length}개</span>
          </div>
        </div>
      </div>

      {/* 액션 버튼 */}
      <div className="flex gap-4 justify-center">
        <button
          onClick={onRestart}
          className="bg-gradient-to-r from-blue-500 to-purple-500 text-white px-6 py-3 rounded-lg font-bold hover:shadow-lg hover:scale-105 transition-all"
        >
          🔄 다시 테스트하기
        </button>
        
        <button
          onClick={() => window.close()}
          className="bg-gray-500 text-white px-6 py-3 rounded-lg font-bold hover:bg-gray-600 transition-colors"
        >
          ✅ 완료
        </button>
      </div>
    </div>
  );
};

export default VideoGazeResult;