-- AI 면접 시스템 초기 데이터베이스 스키마
-- 생성일: 2025-01-22
-- 버전: 1.0.0

-- ===================
-- 확장 기능 활성화
-- ===================

-- UUID 생성을 위한 확장
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 시간 관련 확장
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ===================
-- 사용자 관련 테이블
-- ===================

-- 사용자 테이블
CREATE TABLE users (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 프로필 정보
    phone VARCHAR(20),
    birth_date DATE,
    education TEXT,
    experience_years INTEGER,
    
    -- 선호 설정 (JSONB로 저장)
    preferred_companies JSONB DEFAULT '[]'::jsonb,
    preferred_positions JSONB DEFAULT '[]'::jsonb,
    notification_enabled BOOLEAN DEFAULT true,
    
    -- 인덱스
    CONSTRAINT users_email_check CHECK (email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT users_experience_years_check CHECK (experience_years >= 0)
);

-- ===================
-- 면접 세션 관련 테이블
-- ===================

-- 면접 세션 테이블
CREATE TABLE interview_sessions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- 기본 정보
    company VARCHAR(50) NOT NULL,
    position VARCHAR(100) NOT NULL,
    mode VARCHAR(20) NOT NULL DEFAULT 'normal',
    status VARCHAR(20) NOT NULL DEFAULT 'setup',
    difficulty VARCHAR(10) DEFAULT '중간',
    
    -- 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 설정 정보
    total_questions INTEGER DEFAULT 20,
    current_question_index INTEGER DEFAULT 0,
    time_limit INTEGER, -- 분 단위
    
    -- 결과 정보
    total_score DECIMAL(5,2),
    category_scores JSONB DEFAULT '{}'::jsonb,
    feedback TEXT,
    
    -- AI 경쟁 모드 전용
    comparison_session_id VARCHAR(100),
    ai_session_id VARCHAR(100),
    ai_name VARCHAR(50) DEFAULT '춘식이',
    
    -- 제약 조건
    CONSTRAINT interview_sessions_mode_check CHECK (mode IN ('normal', 'ai_competition', 'group', 'video')),
    CONSTRAINT interview_sessions_status_check CHECK (status IN ('setup', 'in_progress', 'completed', 'paused', 'cancelled')),
    CONSTRAINT interview_sessions_difficulty_check CHECK (difficulty IN ('쉬움', '중간', '어려움')),
    CONSTRAINT interview_sessions_score_check CHECK (total_score >= 0 AND total_score <= 100),
    CONSTRAINT interview_sessions_questions_check CHECK (total_questions > 0 AND current_question_index >= 0)
);

-- AI 경쟁 면접 비교 세션 테이블
CREATE TABLE comparison_sessions (
    id VARCHAR(100) PRIMARY KEY,
    user_session_id UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    ai_session_id VARCHAR(100) NOT NULL,
    
    -- 진행 상황
    current_question_index INTEGER DEFAULT 1,
    current_phase VARCHAR(20) DEFAULT 'user_turn',
    total_questions INTEGER DEFAULT 20,
    
    -- 참여자 정보
    user_name VARCHAR(100) NOT NULL,
    ai_name VARCHAR(50) DEFAULT '춘식이',
    starts_with_user BOOLEAN DEFAULT true,
    
    -- 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- 결과 비교
    user_total_score DECIMAL(5,2),
    ai_total_score DECIMAL(5,2),
    winner VARCHAR(20),
    
    -- 제약 조건
    CONSTRAINT comparison_sessions_phase_check CHECK (current_phase IN ('user_turn', 'ai_turn')),
    CONSTRAINT comparison_sessions_winner_check CHECK (winner IN ('user', 'ai', 'tie'))
);

-- ===================
-- 질문 및 답변 테이블
-- ===================

-- 질문 테이블
CREATE TABLE questions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    
    -- 질문 내용
    question TEXT NOT NULL,
    question_type VARCHAR(20) NOT NULL,
    question_intent TEXT,
    category VARCHAR(50),
    
    -- 메타데이터
    question_index INTEGER NOT NULL,
    is_fixed BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 난이도 및 설정
    difficulty_level VARCHAR(10),
    time_limit INTEGER, -- 초 단위
    
    -- 기업별 커스터마이징
    company_specific JSONB DEFAULT '{}'::jsonb,
    
    -- 제약 조건
    CONSTRAINT questions_type_check CHECK (question_type IN ('INTRO', 'MOTIVATION', 'HR', 'TECH', 'COLLABORATION', 'PROJECT', 'CULTURE')),
    CONSTRAINT questions_index_check CHECK (question_index > 0),
    CONSTRAINT questions_time_limit_check CHECK (time_limit > 0)
);

-- 답변 테이블
CREATE TABLE answers (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    
    -- 답변 내용
    answer TEXT NOT NULL,
    participant_type VARCHAR(10) NOT NULL,
    participant_name VARCHAR(100) NOT NULL,
    
    -- 시간 정보
    time_spent INTEGER NOT NULL, -- 초 단위
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 평가 정보
    score DECIMAL(5,2),
    detailed_scores JSONB DEFAULT '{}'::jsonb,
    feedback TEXT,
    
    -- AI 관련 (AI 답변인 경우)
    ai_persona VARCHAR(50),
    quality_level VARCHAR(20),
    
    -- 분석 데이터
    word_count INTEGER,
    sentiment VARCHAR(20),
    keywords JSONB DEFAULT '[]'::jsonb,
    
    -- 제약 조건
    CONSTRAINT answers_participant_type_check CHECK (participant_type IN ('user', 'ai')),
    CONSTRAINT answers_score_check CHECK (score >= 0 AND score <= 100),
    CONSTRAINT answers_time_spent_check CHECK (time_spent >= 0),
    CONSTRAINT answers_word_count_check CHECK (word_count >= 0)
);

-- ===================
-- 이력서 및 문서 테이블
-- ===================

-- 이력서 테이블
CREATE TABLE resumes (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 파일 정보
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    file_type VARCHAR(10) NOT NULL,
    
    -- 분석 결과
    parsed_content JSONB DEFAULT '{}'::jsonb,
    skills JSONB DEFAULT '[]'::jsonb,
    experience_summary TEXT,
    education_info JSONB DEFAULT '[]'::jsonb,
    
    -- 메타데이터
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    analyzed_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    
    -- 제약 조건
    CONSTRAINT resumes_file_type_check CHECK (file_type IN ('pdf', 'docx', 'txt')),
    CONSTRAINT resumes_file_size_check CHECK (file_size > 0)
);

-- ===================
-- AI 후보자 테이블
-- ===================

-- AI 후보자 테이블
CREATE TABLE ai_candidates (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    
    -- 페르소나 정보
    persona_type VARCHAR(20) NOT NULL,
    personality VARCHAR(50) NOT NULL,
    background JSONB DEFAULT '{}'::jsonb,
    
    -- 성능 설정
    skill_level VARCHAR(20) NOT NULL,
    answer_quality VARCHAR(20) NOT NULL,
    
    -- 통계
    total_interviews INTEGER DEFAULT 0,
    win_rate DECIMAL(5,2),
    average_score DECIMAL(5,2),
    
    -- 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    
    -- 제약 조건
    CONSTRAINT ai_candidates_persona_type_check CHECK (persona_type IN ('junior', 'mid_level', 'senior')),
    CONSTRAINT ai_candidates_skill_level_check CHECK (skill_level IN ('beginner', 'intermediate', 'advanced', 'expert')),
    CONSTRAINT ai_candidates_answer_quality_check CHECK (answer_quality IN ('basic', 'good', 'excellent')),
    CONSTRAINT ai_candidates_win_rate_check CHECK (win_rate >= 0 AND win_rate <= 100),
    CONSTRAINT ai_candidates_average_score_check CHECK (average_score >= 0 AND average_score <= 100)
);

-- ===================
-- 통계 및 분석 테이블
-- ===================

-- 면접 통계 테이블
CREATE TABLE interview_statistics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- 기간별 통계
    period_type VARCHAR(10) NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- 면접 통계
    total_interviews INTEGER DEFAULT 0,
    completed_interviews INTEGER DEFAULT 0,
    ai_competition_count INTEGER DEFAULT 0,
    
    -- 성과 통계
    average_score DECIMAL(5,2),
    best_score DECIMAL(5,2),
    improvement_rate DECIMAL(5,2),
    
    -- 카테고리별 통계
    category_performance JSONB DEFAULT '{}'::jsonb,
    
    -- 기업별 통계
    company_performance JSONB DEFAULT '{}'::jsonb,
    
    -- 메타데이터
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 제약 조건
    CONSTRAINT interview_statistics_period_type_check CHECK (period_type IN ('daily', 'weekly', 'monthly', 'yearly')),
    CONSTRAINT interview_statistics_period_check CHECK (period_end > period_start),
    CONSTRAINT interview_statistics_counts_check CHECK (total_interviews >= 0 AND completed_interviews >= 0 AND ai_competition_count >= 0)
);

-- ===================
-- 시스템 로그 테이블
-- ===================

-- 시스템 로그 테이블
CREATE TABLE system_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    
    -- 로그 기본 정보
    level VARCHAR(10) NOT NULL,
    message TEXT NOT NULL,
    module VARCHAR(100) NOT NULL,
    function VARCHAR(100),
    
    -- 컨텍스트 정보
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id UUID REFERENCES interview_sessions(id) ON DELETE SET NULL,
    request_id VARCHAR(100),
    
    -- 상세 정보
    details JSONB DEFAULT '{}'::jsonb,
    stack_trace TEXT,
    
    -- 메타데이터
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    
    -- 제약 조건
    CONSTRAINT system_logs_level_check CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'))
);

-- ===================
-- 인덱스 생성
-- ===================

-- 사용자 테이블 인덱스
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);

-- 면접 세션 테이블 인덱스
CREATE INDEX idx_interview_sessions_user_id ON interview_sessions(user_id);
CREATE INDEX idx_interview_sessions_status ON interview_sessions(status);
CREATE INDEX idx_interview_sessions_mode ON interview_sessions(mode);
CREATE INDEX idx_interview_sessions_company ON interview_sessions(company);
CREATE INDEX idx_interview_sessions_created_at ON interview_sessions(created_at);
CREATE INDEX idx_interview_sessions_comparison_id ON interview_sessions(comparison_session_id);

-- 비교 세션 테이블 인덱스
CREATE INDEX idx_comparison_sessions_user_session ON comparison_sessions(user_session_id);
CREATE INDEX idx_comparison_sessions_created_at ON comparison_sessions(created_at);

-- 질문 테이블 인덱스
CREATE INDEX idx_questions_session_id ON questions(session_id);
CREATE INDEX idx_questions_type ON questions(question_type);
CREATE INDEX idx_questions_index ON questions(question_index);
CREATE INDEX idx_questions_created_at ON questions(created_at);

-- 답변 테이블 인덱스
CREATE INDEX idx_answers_session_id ON answers(session_id);
CREATE INDEX idx_answers_question_id ON answers(question_id);
CREATE INDEX idx_answers_participant_type ON answers(participant_type);
CREATE INDEX idx_answers_submitted_at ON answers(submitted_at);

-- 이력서 테이블 인덱스
CREATE INDEX idx_resumes_user_id ON resumes(user_id);
CREATE INDEX idx_resumes_uploaded_at ON resumes(uploaded_at);
CREATE INDEX idx_resumes_is_active ON resumes(is_active);

-- AI 후보자 테이블 인덱스
CREATE INDEX idx_ai_candidates_persona_type ON ai_candidates(persona_type);
CREATE INDEX idx_ai_candidates_is_active ON ai_candidates(is_active);

-- 통계 테이블 인덱스
CREATE INDEX idx_interview_statistics_user_id ON interview_statistics(user_id);
CREATE INDEX idx_interview_statistics_period ON interview_statistics(period_type, period_start, period_end);

-- 시스템 로그 테이블 인덱스
CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX idx_system_logs_user_id ON system_logs(user_id);
CREATE INDEX idx_system_logs_session_id ON system_logs(session_id);

-- ===================
-- 트리거 함수 생성
-- ===================

-- updated_at 자동 업데이트 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- updated_at 트리거 적용
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_interview_sessions_updated_at 
    BEFORE UPDATE ON interview_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_candidates_updated_at 
    BEFORE UPDATE ON ai_candidates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===================
-- Row Level Security (RLS) 설정
-- ===================

-- 사용자 테이블 RLS 활성화
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- 사용자는 자신의 데이터만 조회/수정 가능
CREATE POLICY users_policy ON users
    FOR ALL USING (auth.uid() = id);

-- 면접 세션 테이블 RLS 활성화
ALTER TABLE interview_sessions ENABLE ROW LEVEL SECURITY;

-- 사용자는 자신의 면접 세션만 접근 가능
CREATE POLICY interview_sessions_policy ON interview_sessions
    FOR ALL USING (user_id = auth.uid());

-- 기타 테이블들도 동일하게 적용
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
CREATE POLICY questions_policy ON questions
    FOR ALL USING (
        session_id IN (
            SELECT id FROM interview_sessions WHERE user_id = auth.uid()
        )
    );

ALTER TABLE answers ENABLE ROW LEVEL SECURITY;
CREATE POLICY answers_policy ON answers
    FOR ALL USING (
        session_id IN (
            SELECT id FROM interview_sessions WHERE user_id = auth.uid()
        )
    );

ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;
CREATE POLICY resumes_policy ON resumes
    FOR ALL USING (user_id = auth.uid());

ALTER TABLE interview_statistics ENABLE ROW LEVEL SECURITY;
CREATE POLICY interview_statistics_policy ON interview_statistics
    FOR ALL USING (user_id = auth.uid());

-- ===================
-- 초기 데이터 삽입
-- ===================

-- 기본 AI 후보자 데이터
INSERT INTO ai_candidates (id, name, persona_type, personality, skill_level, answer_quality, background) VALUES
('chunsik_junior', '춘식이 (주니어)', 'junior', 'humble', 'intermediate', 'good', '{"experience": "1-2년", "education": "학사", "specialty": "웹 개발"}'),
('chunsik_mid', '춘식이 (미들)', 'mid_level', 'confident', 'advanced', 'excellent', '{"experience": "3-5년", "education": "학사", "specialty": "백엔드 개발"}'),
('chunsik_senior', '춘식이 (시니어)', 'senior', 'analytical', 'expert', 'excellent', '{"experience": "5년+", "education": "석사", "specialty": "시스템 아키텍처"}');

-- 인덱스 통계 업데이트
ANALYZE;