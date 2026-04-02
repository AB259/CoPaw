-- -*- coding: utf-8 -*-
-- Instance management database schema
-- User instance allocation feature

-- 实例表
CREATE TABLE IF NOT EXISTS swe_instance_info (
    instance_id VARCHAR(64) PRIMARY KEY COMMENT '实例ID',
    source_id VARCHAR(64) NOT NULL COMMENT '所属来源ID',
    bbk_id VARCHAR(64) DEFAULT NULL COMMENT '所属分行ID（可空）',
    instance_name VARCHAR(128) NOT NULL COMMENT '实例名称',
    instance_url VARCHAR(512) NOT NULL COMMENT '实例URL地址',
    max_users INT NOT NULL DEFAULT 100 COMMENT '用户量阈值',
    status ENUM('active', 'inactive') DEFAULT 'active' COMMENT '实例状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_source_id (source_id),
    INDEX idx_bbk_id (bbk_id)
) COMMENT '实例信息表';

-- 用户分配表
CREATE TABLE IF NOT EXISTS swe_instance_user (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL COMMENT '用户ID',
    source_id VARCHAR(64) NOT NULL COMMENT '所属来源ID',
    bbk_id VARCHAR(64) DEFAULT NULL COMMENT '所属分行ID（可空）',
    instance_id VARCHAR(64) NOT NULL COMMENT '分配的实例ID',
    allocated_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '分配时间',
    status ENUM('active', 'migrated') DEFAULT 'active' COMMENT '分配状态',
    UNIQUE KEY uk_user_source_bbk (user_id, source_id, IFNULL(bbk_id, 'NULL')),
    INDEX idx_source_id (source_id),
    INDEX idx_bbk_id (bbk_id),
    INDEX idx_instance_id (instance_id)
) COMMENT '用户实例分配表';

-- 操作日志表
CREATE TABLE IF NOT EXISTS swe_instance_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    action VARCHAR(32) NOT NULL COMMENT '操作类型',
    target_type VARCHAR(32) NOT NULL COMMENT '目标类型',
    target_id VARCHAR(128) NOT NULL COMMENT '目标ID',
    old_value JSON COMMENT '旧值',
    new_value JSON COMMENT '新值',
    operator VARCHAR(128) COMMENT '操作人',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_target (target_type, target_id),
    INDEX idx_created_at (created_at)
) COMMENT '操作日志表';
