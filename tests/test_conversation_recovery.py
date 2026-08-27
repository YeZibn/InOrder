from inorder_llm.context import HistoryConversation, prepare_conversation_recovery


def history(*turns):
    value = HistoryConversation()
    for role, content in turns:
        value.append(role, content)
    return value


def test_complete_history_only_processes_new_message():
    result = prepare_conversation_recovery(history(("user", "上一轮"), ("assistant", "已完成")), "新消息")
    assert result.recovered is False
    assert result.message == "新消息"
    assert [turn.content for turn in result.history.turns] == ["上一轮", "已完成"]


def test_pending_user_is_replayed_without_duplicate_history():
    result = prepare_conversation_recovery(history(("user", "我要运苹果")), "重试")
    assert result.recovered and result.is_retry
    assert result.message == "我要运苹果"
    assert result.history.turns == []


def test_pending_user_merges_with_new_business_message():
    result = prepare_conversation_recovery(history(("user", "我要运苹果")), "从温州到上海")
    assert result.message == "我要运苹果\n从温州到上海"
    assert result.history.turns == []


def test_consecutive_pending_users_are_merged_and_deduplicated():
    result = prepare_conversation_recovery(history(("assistant", "上一轮"), ("user", "我要运苹果"), ("user", "从温州到上海")), "从温州到上海")
    assert result.message == "我要运苹果\n从温州到上海"
    assert result.pending_messages == ("我要运苹果", "从温州到上海")


def test_recovered_history_has_one_user_and_assistant_turn():
    result = prepare_conversation_recovery(history(("user", "我要运苹果")), "明天下午")
    completed = result.recovered_history("已完成")
    assert [(turn.role, turn.content) for turn in completed.turns] == [("user", "我要运苹果\n明天下午"), ("assistant", "已完成")]
