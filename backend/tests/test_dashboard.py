"""Testes da US-06 — Dashboard de Análise."""

import json
import uuid
from datetime import datetime, timedelta

from models.annotation import Annotation, AnnotationConflict
from models.collection import Collection, Comment
from models.dataset import Dataset, DatasetEntry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_collection(db, user_id, *, video_id="vid123", status="completed"):
    col = Collection(
        video_id=video_id,
        status=status,
        collected_by=user_id,
        total_comments=5,
    )
    db.add(col)
    db.flush()
    return col


def _make_comments(db, collection_id, author_channel_id, count=5, base_date=None):
    if base_date is None:
        base_date = datetime(2024, 6, 15)
    comments = []
    for i in range(count):
        c = Comment(
            collection_id=collection_id,
            comment_id=f"{author_channel_id}_c{i}_{uuid.uuid4().hex[:4]}",
            author_channel_id=author_channel_id,
            author_display_name=f"User {author_channel_id}",
            text_original=f"Comentario {i} do {author_channel_id}",
            like_count=i * 2,
            reply_count=0,
            published_at=base_date + timedelta(hours=i),
            updated_at=base_date + timedelta(hours=i),
        )
        db.add(c)
        comments.append(c)
    db.flush()
    return comments


def _make_dataset(
    db, collection_id, user_id, author_channel_ids, criteria=None, name=None
):
    if criteria is None:
        criteria = ["percentil"]
    ds = Dataset(
        name=name or f"ds_{uuid.uuid4().hex[:6]}",
        collection_id=collection_id,
        criteria_applied=criteria,
        thresholds={},
        total_users_original=10,
        total_users_selected=len(author_channel_ids),
        created_by=user_id,
    )
    db.add(ds)
    db.flush()
    entries = []
    for channel_id in author_channel_ids:
        entry = DatasetEntry(
            dataset_id=ds.id,
            author_channel_id=channel_id,
            author_display_name=f"User {channel_id}",
            comment_count=5,
            matched_criteria=criteria,
        )
        db.add(entry)
        entries.append(entry)
    db.flush()
    return ds, entries


def _annotate(db, entry, user, label, justificativa=None):
    ann = Annotation(
        dataset_entry_id=entry.id,
        annotator_id=user.id,
        label=label,
        justificativa=justificativa,
        annotated_at=datetime(2024, 7, 1, 10, 0),
    )
    db.add(ann)
    db.flush()
    return ann


def _make_conflict(
    db,
    entry,
    ann_a,
    ann_b,
    *,
    resolved_by=None,
    resolved_label=None,
    status="pending",
):
    conflict = AnnotationConflict(
        dataset_entry_id=entry.id,
        annotation_a_id=ann_a.id,
        annotation_b_id=ann_b.id,
        status=status,
        resolved_by=resolved_by,
        resolved_label=resolved_label,
        resolved_at=datetime(2024, 7, 5) if status == "resolved" else None,
    )
    db.add(conflict)
    db.flush()
    return conflict


def _assert_valid_plotly_json(chart_json: str):
    """Verifica que o chart é JSON parseável com chaves data e layout."""
    fig = json.loads(chart_json)
    assert "data" in fig, "Plotly JSON deve conter 'data'"
    assert "layout" in fig, "Plotly JSON deve conter 'layout'"


def _populate_full_scenario(db, user_a, user_b):
    """Cria cenário completo: 2 vídeos, 3 datasets, anotações por entry.

    Unidade de anotação: entry (autor/canal do YouTube).
    Retorna dict com referências para assertions nos testes.
    """
    # Vídeo 1 — 2 datasets com critérios diferentes
    col1 = _make_collection(db, user_a.id, video_id="vid_alpha")
    _make_comments(db, col1.id, "author_a", count=3)
    _make_comments(db, col1.id, "author_b", count=2)

    ds1, entries1 = _make_dataset(
        db,
        col1.id,
        user_a.id,
        ["author_a"],
        criteria=["percentil"],
        name="alpha_percentil",
    )
    ds2, entries2 = _make_dataset(
        db,
        col1.id,
        user_a.id,
        ["author_b"],
        criteria=["media", "curtos"],
        name="alpha_media_curtos",
    )

    # Vídeo 2 — 1 dataset com 2 autores
    col2 = _make_collection(db, user_a.id, video_id="vid_beta")
    _make_comments(db, col2.id, "author_c", count=4)
    _make_comments(db, col2.id, "author_d", count=2)
    ds3, entries3 = _make_dataset(
        db,
        col2.id,
        user_a.id,
        ["author_c", "author_d"],
        criteria=["percentil", "identicos"],
        name="beta_percentil_identicos",
    )

    entry_a = entries1[0]  # author_a
    entry_b = entries2[0]  # author_b
    entry_c = entries3[0]  # author_c
    entry_d = entries3[1]  # author_d

    # ── Anotações por entry (usuario) ──

    # entry_a (author_a): conflito pendente (A=bot, B=humano)
    ann_ea_a = _annotate(db, entry_a, user_a, "bot", "suspeito")
    ann_ea_b = _annotate(db, entry_a, user_b, "humano")
    _make_conflict(db, entry_a, ann_ea_a, ann_ea_b, status="pending")

    # entry_b (author_b): conflito resolvido como bot
    ann_eb_a = _annotate(db, entry_b, user_a, "bot", "repetitivo")
    ann_eb_b = _annotate(db, entry_b, user_b, "humano")
    _make_conflict(
        db,
        entry_b,
        ann_eb_a,
        ann_eb_b,
        status="resolved",
        resolved_by=user_a.id,
        resolved_label="bot",
    )

    # entry_c (author_c): consenso humano
    _annotate(db, entry_c, user_a, "humano")
    _annotate(db, entry_c, user_b, "humano")

    # entry_d (author_d): consenso bot
    _annotate(db, entry_d, user_a, "bot", "bot óbvio")
    _annotate(db, entry_d, user_b, "bot", "concordo")

    db.commit()

    return {
        "col1": col1,
        "col2": col2,
        "ds1": ds1,
        "ds2": ds2,
        "ds3": ds3,
        "entry_a": entry_a,
        "entry_b": entry_b,
        "entry_c": entry_c,
        "entry_d": entry_d,
    }


# ---------------------------------------------------------------------------
# GET /dashboard/global
# ---------------------------------------------------------------------------


class TestGlobalDashboard:
    def test_retorna_kpis_e_charts_validos(self, client, db, auth_as_user, admin_user):
        """KPIs corretos e todos os charts são JSON Plotly válidos."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/global")
        assert resp.status_code == 200
        data = resp.json()

        s = data["summary"]
        assert s["total_datasets"] == 3
        # bots: resolvido bot (entry_b) + consenso bot (entry_d) = 2
        assert s["total_bots"] == 2
        # humanos: consenso humano (entry_c) = 1
        assert s["total_humans"] == 1
        # conflitos totais: 2 (pendente entry_a + resolvido entry_b)
        assert s["total_conflicts"] == 2
        assert s["pending_conflicts"] == 1

        # Progresso geral
        assert s["total_users_in_datasets"] == 4
        assert 0 <= s["annotation_progress"] <= 100

        # Charts válidos
        for key in [
            "label_distribution_chart",
            "comparativo_por_dataset_chart",
            "annotations_over_time_chart",
            "bot_rate_by_dataset_chart",
            "agreement_by_dataset_chart",
            "criteria_effectiveness_chart",
        ]:
            _assert_valid_plotly_json(data[key])

    def test_sem_token_retorna_401(self, client):
        resp = client.get("/dashboard/global")
        assert resp.status_code == 401

    def test_sem_dados_retorna_zeros(self, client, auth_as_user):
        """Banco vazio retorna zeros e charts válidos — nunca 404."""
        resp = client.get("/dashboard/global")
        assert resp.status_code == 200
        data = resp.json()
        s = data["summary"]
        assert s["total_datasets"] == 0
        assert s["total_bots"] == 0
        assert s["total_humans"] == 0
        assert s["agreement_rate"] == 0.0
        _assert_valid_plotly_json(data["label_distribution_chart"])

    def test_filtro_criteria_filtra_datasets(
        self, client, db, auth_as_user, admin_user
    ):
        """Filtrar por criteria=percentil retorna apenas datasets com percentil."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/global?criteria=percentil")
        assert resp.status_code == 200
        data = resp.json()

        # Datasets com percentil: alpha_percentil e beta_percentil_identicos
        assert data["summary"]["total_datasets"] == 2
        assert data["active_criteria_filter"] == ["percentil"]

    def test_filtro_criteria_multiplo(self, client, db, auth_as_user, admin_user):
        """criteria=percentil,identicos retorna apenas datasets com AMBOS."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/global?criteria=percentil,identicos")
        assert resp.status_code == 200
        data = resp.json()

        # Apenas beta_percentil_identicos tem ambos
        assert data["summary"]["total_datasets"] == 1

    def test_agreement_rate_correto(self, client, db, auth_as_user, admin_user):
        """Agreement = consenso / total com 2 anotações."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/global")
        data = resp.json()
        rate = data["summary"]["agreement_rate"]

        # Com 2 anotações (por entry):
        # entry_a: conflito (diverge) → 0
        # entry_b: conflito (diverge) → 0
        # entry_c: consenso humano → 1
        # entry_d: consenso bot → 1
        # Total: 2 consenso / 4 = 0.5
        assert rate == round(2 / 4, 4)


# ---------------------------------------------------------------------------
# GET /dashboard/video
# ---------------------------------------------------------------------------


class TestVideoDashboard:
    def test_retorna_dados_do_video_filtrado(
        self, client, db, auth_as_user, admin_user
    ):
        """Apenas dados do video_id requisitado."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/video?video_id=vid_alpha")
        assert resp.status_code == 200
        data = resp.json()

        assert data["video_id"] == "vid_alpha"
        s = data["summary"]
        # vid_alpha tem 5 comentários coletados (3 de author_a + 2 de author_b)
        assert s["total_comments_collected"] == 5
        # 2 entries (author_a + author_b)
        assert s["total_users_in_datasets"] == 2

        # Charts válidos
        for key in [
            "label_distribution_chart",
            "comparativo_por_dataset_chart",
            "bot_rate_by_criteria_chart",
            "comment_timeline_chart",
        ]:
            _assert_valid_plotly_json(data[key])

    def test_sem_token_retorna_401(self, client):
        resp = client.get("/dashboard/video?video_id=vid_alpha")
        assert resp.status_code == 401

    def test_video_inexistente_retorna_zeros(self, client, db, auth_as_user):
        """video_id que não existe retorna 200 com zeros — nunca 404."""
        resp = client.get("/dashboard/video?video_id=inexistente")
        assert resp.status_code == 200
        data = resp.json()
        s = data["summary"]
        assert s["total_comments_collected"] == 0
        assert s["total_annotated"] == 0
        assert s["total_bots"] == 0

    def test_video_com_filtro_criteria(self, client, db, auth_as_user, admin_user):
        """Filtro por critério no contexto de um vídeo."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/video?video_id=vid_alpha&criteria=media,curtos")
        assert resp.status_code == 200
        data = resp.json()

        # Apenas alpha_media_curtos tem ambos media e curtos (1 entry: author_b)
        assert data["summary"]["total_users_in_datasets"] == 1


# ---------------------------------------------------------------------------
# GET /dashboard/user
# ---------------------------------------------------------------------------


class TestUserDashboard:
    def test_retorna_dados_do_pesquisador_autenticado(
        self, client, db, auth_as_user, admin_user
    ):
        """Apenas anotações do usuário autenticado (auth_as_user)."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/user")
        assert resp.status_code == 200
        data = resp.json()

        s = data["summary"]
        # auth_as_user (user_a) anotou por entry:
        # entry_a=bot, entry_b=bot, entry_c=humano, entry_d=bot
        # Total: 4 anotados, bots=3, humans=1
        assert s["total_annotated"] == 4
        assert s["bots"] == 3
        assert s["humans"] == 1
        assert s["total_datasets_assigned"] == 3
        assert len(data["datasets"]) == 3

        # Charts válidos
        for key in [
            "my_label_distribution_chart",
            "my_progress_by_dataset_chart",
            "my_annotations_over_time_chart",
        ]:
            _assert_valid_plotly_json(data[key])

    def test_sem_token_retorna_401(self, client):
        resp = client.get("/dashboard/user")
        assert resp.status_code == 401

    def test_nao_expoe_dados_de_outro_pesquisador(
        self, client, db, auth_as_user, admin_user
    ):
        """Dados do admin_user não aparecem no dashboard do auth_as_user."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/user")
        assert resp.status_code == 200
        text = resp.text

        # Username do admin não deve aparecer em nenhum campo
        assert admin_user.username not in text

    def test_sem_dados_retorna_zeros(self, client, auth_as_user):
        """Sem datasets retorna zeros e charts válidos."""
        resp = client.get("/dashboard/user")
        assert resp.status_code == 200
        data = resp.json()
        s = data["summary"]
        assert s["total_datasets_assigned"] == 0
        assert s["total_annotated"] == 0
        assert s["bots"] == 0
        assert data["datasets"] == []
        _assert_valid_plotly_json(data["my_label_distribution_chart"])

    def test_dataset_status_correto(self, client, db, auth_as_user, admin_user):
        """Verifica status completed, in_progress e not_started."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_status")
        _make_comments(db, col.id, "ch_a", count=2)
        _make_comments(db, col.id, "ch_b1", count=2)
        _make_comments(db, col.id, "ch_b2", count=2)
        _make_comments(db, col.id, "ch_c", count=2)

        ds_done, entries_done = _make_dataset(
            db, col.id, auth_as_user.id, ["ch_a"], name="ds_done"
        )
        ds_partial, entries_partial = _make_dataset(
            db, col.id, auth_as_user.id, ["ch_b1", "ch_b2"], name="ds_partial"
        )
        _make_dataset(db, col.id, auth_as_user.id, ["ch_c"], name="ds_empty")

        # ds_done: anotar todos os entries (1 entry)
        _annotate(db, entries_done[0], auth_as_user, "humano")

        # ds_partial: anotar 1 de 2 entries
        _annotate(db, entries_partial[0], auth_as_user, "bot", "teste")

        # ds_empty: nenhuma anotação
        db.commit()

        resp = client.get("/dashboard/user")
        data = resp.json()

        ds_map = {d["dataset_name"]: d for d in data["datasets"]}
        assert ds_map["ds_done"]["status"] == "completed"
        assert ds_map["ds_done"]["percent_complete"] == 100.0
        assert ds_map["ds_partial"]["status"] == "in_progress"
        assert ds_map["ds_partial"]["percent_complete"] == 50.0
        assert ds_map["ds_empty"]["status"] == "not_started"
        assert ds_map["ds_empty"]["percent_complete"] == 0.0


# ---------------------------------------------------------------------------
# GET /dashboard/bots
# ---------------------------------------------------------------------------


class TestBotComments:
    def test_retorna_bots_com_concordancia(self, client, db, auth_as_user, admin_user):
        """Tabela de bots retorna concordance_pct correto."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_bots")
        _make_comments(db, col.id, "ch_bot", count=2)
        ds, entries = _make_dataset(db, col.id, auth_as_user.id, ["ch_bot"])
        entry = entries[0]

        # Consenso bot no entry
        _annotate(db, entry, auth_as_user, "bot", "spam")
        _annotate(db, entry, admin_user, "bot", "concordo")
        db.commit()

        resp = client.get("/dashboard/bots")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total"] >= 1
        # Consenso bot → 100%
        bot_items = [i for i in data["items"] if i["concordance_pct"] == 100]
        assert len(bot_items) >= 1

    def test_sem_token_retorna_401(self, client):
        resp = client.get("/dashboard/bots")
        assert resp.status_code == 401

    def test_filtro_por_author(self, client, db, auth_as_user, admin_user):
        """Filtro de busca por author_display_name."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_search")
        _make_comments(db, col.id, "ch_search", count=1)
        ds, entries = _make_dataset(db, col.id, auth_as_user.id, ["ch_search"])
        _annotate(db, entries[0], auth_as_user, "bot", "teste busca")
        db.commit()

        resp = client.get("/dashboard/bots?author=ch_search")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1


# ---------------------------------------------------------------------------
# GET /dashboard/criteria-effectiveness
# ---------------------------------------------------------------------------


class TestCriteriaEffectiveness:
    def test_retorna_eficacia_por_criterio(self, client, db, auth_as_user, admin_user):
        """Cada critério retorna total_datasets, total_bots e bot_rate."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/criteria-effectiveness")
        assert resp.status_code == 200
        data = resp.json()

        assert len(data) > 0
        for item in data:
            assert "criteria" in item
            assert "group" in item
            assert item["group"] in ("numerico", "comportamental")
            assert "total_datasets" in item
            assert "bot_rate" in item

        # percentil aparece em 2 datasets
        percentil = next(i for i in data if i["criteria"] == "percentil")
        assert percentil["total_datasets"] == 2

    def test_sem_token_retorna_401(self, client):
        resp = client.get("/dashboard/criteria-effectiveness")
        assert resp.status_code == 401

    def test_filtro_por_video_id(self, client, db, auth_as_user, admin_user):
        """Filtra eficácia por vídeo específico."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/criteria-effectiveness?video_id=vid_alpha")
        assert resp.status_code == 200
        data = resp.json()

        criterios = {i["criteria"] for i in data}
        # vid_alpha tem percentil e media+curtos
        assert "percentil" in criterios
        assert "media" in criterios
        # identicos é do vid_beta — não deve aparecer
        assert "identicos" not in criterios

    def test_sem_dados_retorna_vazio(self, client, auth_as_user):
        resp = client.get("/dashboard/criteria-effectiveness")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Segurança — nenhum endpoint expõe username de outro pesquisador
# ---------------------------------------------------------------------------


class TestSeguranca:
    def test_global_nao_expoe_username(self, client, db, auth_as_user, admin_user):
        """Visão geral não expõe username de nenhum pesquisador."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/global")
        text = resp.text
        assert admin_user.username not in text
        assert auth_as_user.username not in text

    def test_video_nao_expoe_username(self, client, db, auth_as_user, admin_user):
        """Por Vídeo não expõe username de nenhum pesquisador."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/video?video_id=vid_alpha")
        text = resp.text
        assert admin_user.username not in text
        assert auth_as_user.username not in text


# ---------------------------------------------------------------------------
# Cobertura adicional — edge cases do serviço dashboard
# ---------------------------------------------------------------------------


class TestClassifyEntrySingleLabel:
    def test_single_annotation_consensus(self, client, db, auth_as_user, admin_user):
        """1 anotacao apenas classifica pelo label unico."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_single")
        _make_comments(db, col.id, "ch_single_a", count=1)
        _make_comments(db, col.id, "ch_single_b", count=1)
        ds, entries = _make_dataset(
            db,
            col.id,
            auth_as_user.id,
            ["ch_single_a", "ch_single_b"],
            name="ds_single",
        )

        _annotate(db, entries[0], auth_as_user, "bot", "unico")
        _annotate(db, entries[1], auth_as_user, "humano")
        db.commit()

        resp = client.get("/dashboard/global")
        assert resp.status_code == 200
        s = resp.json()["summary"]
        assert s["total_bots"] >= 1
        assert s["total_humans"] >= 1


class TestBotRateChartNonHorizontal:
    def test_bot_rate_vertical_orientation(self, client, db, auth_as_user, admin_user):
        """Gráfico de taxa de bots com orientacao vertical."""
        from services.dashboard import _make_bot_rate_chart

        data = [
            {"name": "ds1", "bot_rate": 50.0},
            {"name": "ds2", "bot_rate": 5.0},
        ]
        chart_json = _make_bot_rate_chart(data, orientation="v")
        _assert_valid_plotly_json(chart_json)
        parsed = json.loads(chart_json)
        # Vertical bar: x should have names
        assert "ds1" in str(parsed["data"])


class TestGlobalDatasetNoComments:
    def test_dataset_with_no_comments_skipped(self, client, db, auth_as_user):
        """Dataset sem entries e sem comentários nao quebra."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_empty_ds")
        # Dataset sem entries
        ds = Dataset(
            name="empty_ds",
            collection_id=col.id,
            criteria_applied=["percentil"],
            thresholds={},
            total_users_original=0,
            total_users_selected=0,
            created_by=auth_as_user.id,
        )
        db.add(ds)
        db.commit()

        resp = client.get("/dashboard/user")
        assert resp.status_code == 200
        # O dataset vazio deve ser ignorado (0 comments)
        data = resp.json()
        assert data["summary"]["total_datasets_assigned"] == 0


class TestBotUsersFilters:
    def test_filter_by_dataset_id(self, client, db, auth_as_user, admin_user):
        """Filtro por dataset_id retorna apenas bots daquele ds."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_filt_ds")
        _make_comments(db, col.id, "ch_fa", count=2)
        _make_comments(db, col.id, "ch_fb", count=2)
        ds_a, entries_a = _make_dataset(
            db,
            col.id,
            auth_as_user.id,
            ["ch_fa"],
            name="ds_filt_a",
        )
        ds_b, entries_b = _make_dataset(
            db,
            col.id,
            auth_as_user.id,
            ["ch_fb"],
            name="ds_filt_b",
        )

        _annotate(db, entries_a[0], auth_as_user, "bot", "spam")
        _annotate(db, entries_b[0], auth_as_user, "bot", "spam")
        db.commit()

        resp = client.get(f"/dashboard/bots?dataset_id={ds_a.id}")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["dataset_name"] == "ds_filt_a"

    def test_filter_by_video_id(self, client, db, auth_as_user):
        """Filtro por video_id retorna bots daquele video."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_filt_vid")
        _make_comments(db, col.id, "ch_fv", count=2)
        ds, entries = _make_dataset(
            db,
            col.id,
            auth_as_user.id,
            ["ch_fv"],
            name="ds_fv",
        )
        _annotate(db, entries[0], auth_as_user, "bot", "teste")
        db.commit()

        resp = client.get("/dashboard/bots?video_id=vid_filt_vid")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_by_author(self, client, db, auth_as_user):
        """Filtro por author busca por display name."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_filt_auth")
        _make_comments(db, col.id, "ch_auth_filt", count=2)
        ds, entries = _make_dataset(
            db,
            col.id,
            auth_as_user.id,
            ["ch_auth_filt"],
            name="ds_auth_filt",
        )
        _annotate(db, entries[0], auth_as_user, "bot", "teste")
        db.commit()

        resp = client.get("/dashboard/bots?author=ch_auth_filt")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_filter_by_criteria(self, client, db, auth_as_user):
        """Filtro por criteria retorna bots de datasets com aquele criterio."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_filt_crit")
        _make_comments(db, col.id, "ch_crit", count=2)
        ds, entries = _make_dataset(
            db,
            col.id,
            auth_as_user.id,
            ["ch_crit"],
            criteria=["intervalo"],
            name="ds_crit",
        )
        _annotate(db, entries[0], auth_as_user, "bot", "teste")
        db.commit()

        resp = client.get("/dashboard/bots?criteria=intervalo")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


class TestHighlightsTextTruncation:
    def test_long_text_truncated_in_highlights(self, client, db, auth_as_user):
        """Comentarios com >60 chars sao truncados nos highlights."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_trunc")
        long_text = "A" * 80
        c = Comment(
            collection_id=col.id,
            comment_id="trunc_c1",
            author_channel_id="ch_trunc",
            author_display_name="Truncador",
            text_original=long_text,
            like_count=100,
            reply_count=50,
            published_at=datetime(2024, 6, 1),
            updated_at=datetime(2024, 6, 1),
        )
        db.add(c)
        db.commit()

        resp = client.get("/dashboard/video?video_id=vid_trunc")
        assert resp.status_code == 200
        highlights = resp.json()["highlights"]

        # Find highlights with truncated text
        truncated = [h for h in highlights if h.get("detail", "").endswith("...")]
        assert len(truncated) >= 1
        for h in truncated:
            # detail should be 63 chars (60 + "...")
            assert len(h["detail"]) <= 63


class TestOldestAccountPreEpochFilter:
    def test_pre_1970_date_filtered_from_oldest(self, client, db, auth_as_user):
        """Conta com data pre-1970 (epoch) nao aparece como mais antiga."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_epoch")
        # Canal com data epoch (1970-01-01) — deve ser filtrado
        c_epoch = Comment(
            collection_id=col.id,
            comment_id="epoch_c1",
            author_channel_id="ch_epoch",
            author_display_name="Epoch Bot",
            text_original="Bot com data epoch",
            like_count=0,
            reply_count=0,
            published_at=datetime(2024, 6, 1),
            updated_at=datetime(2024, 6, 1),
            author_channel_published_at=datetime(1970, 1, 1),
        )
        # Canal com data valida
        c_valid = Comment(
            collection_id=col.id,
            comment_id="valid_c1",
            author_channel_id="ch_valid",
            author_display_name="Valid Human",
            text_original="Humano com data valida",
            like_count=0,
            reply_count=0,
            published_at=datetime(2024, 6, 1),
            updated_at=datetime(2024, 6, 1),
            author_channel_published_at=datetime(2015, 3, 15),
        )
        db.add_all([c_epoch, c_valid])
        db.commit()

        resp = client.get("/dashboard/video?video_id=vid_epoch")
        assert resp.status_code == 200
        highlights = resp.json()["highlights"]

        oldest_items = [h for h in highlights if h["label"] == "Conta mais antiga"]
        # Should show Valid Human, not Epoch Bot
        if oldest_items:
            assert oldest_items[0]["value"] == "Valid Human"
            assert "1970" not in oldest_items[0]["detail"]


class TestEmptyAuthorSetSkip:
    def test_dataset_with_entries_but_no_matching_comments(
        self, client, db, auth_as_user
    ):
        """Dataset com entry apontando para autor sem comentarios."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_no_match")
        # Dataset entry aponta para autor que nao tem
        # comentarios nesta coleta
        ds = Dataset(
            name="ds_no_match",
            collection_id=col.id,
            criteria_applied=["percentil"],
            thresholds={},
            total_users_original=1,
            total_users_selected=1,
            created_by=auth_as_user.id,
        )
        db.add(ds)
        db.flush()
        entry = DatasetEntry(
            dataset_id=ds.id,
            author_channel_id="ch_ghost",
            author_display_name="Ghost",
            comment_count=0,
            matched_criteria=["percentil"],
        )
        db.add(entry)
        db.commit()

        resp = client.get("/dashboard/global")
        assert resp.status_code == 200
        s = resp.json()["summary"]
        # Entry existe mas sem comentários — ainda conta como usuário no dataset
        assert s["total_users_in_datasets"] == 1


class TestBotRateByCriteriaEmptyCids:
    def test_dataset_with_ghost_entries_skipped_in_bot_rate(
        self, client, db, auth_as_user
    ):
        """Dataset com entries sem comentarios reais e ignorado."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_ghost_br")
        ds = Dataset(
            name="ds_ghost_br",
            collection_id=col.id,
            criteria_applied=["percentil"],
            thresholds={},
            total_users_original=1,
            total_users_selected=1,
            created_by=auth_as_user.id,
        )
        db.add(ds)
        db.flush()
        entry = DatasetEntry(
            dataset_id=ds.id,
            author_channel_id="ch_ghost_br",
            author_display_name="Ghost",
            comment_count=0,
            matched_criteria=["percentil"],
        )
        db.add(entry)
        db.commit()

        resp = client.get("/dashboard/video?video_id=vid_ghost_br")
        assert resp.status_code == 200
        _assert_valid_plotly_json(resp.json()["bot_rate_by_criteria_chart"])


class TestClassifyEntryMultiLabelNoConflict:
    def test_divergent_labels_without_conflict_returns_none(
        self, client, db, auth_as_user, admin_user
    ):
        """Anotacoes divergentes sem AnnotationConflict: classificacao None."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_noconf")
        _make_comments(db, col.id, "ch_noconf", count=1)
        ds, entries = _make_dataset(
            db,
            col.id,
            auth_as_user.id,
            ["ch_noconf"],
            name="ds_noconf",
        )

        # Inserir anotacoes divergentes SEM conflito
        ann_a = Annotation(
            dataset_entry_id=entries[0].id,
            annotator_id=auth_as_user.id,
            label="bot",
            justificativa="suspeito",
        )
        ann_b = Annotation(
            dataset_entry_id=entries[0].id,
            annotator_id=admin_user.id,
            label="humano",
        )
        db.add_all([ann_a, ann_b])
        db.commit()

        resp = client.get("/dashboard/global")
        assert resp.status_code == 200
        # O entry nao eh classificado (None)
        s = resp.json()["summary"]
        assert s["total_bots"] == 0
        assert s["total_humans"] == 0


class TestOldestAccountHighlightShown:
    def test_oldest_account_with_valid_year_shown(self, client, db, auth_as_user):
        """Conta antiga com year > 1970 aparece nos highlights."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_old_ok")
        c = Comment(
            collection_id=col.id,
            comment_id="old_ok_c1",
            author_channel_id="ch_old_ok",
            author_display_name="Old Account",
            text_original="Conta de 2015",
            like_count=0,
            reply_count=0,
            published_at=datetime(2024, 6, 1),
            updated_at=datetime(2024, 6, 1),
            author_channel_published_at=datetime(2015, 6, 15),
        )
        db.add(c)
        db.commit()

        resp = client.get("/dashboard/video?video_id=vid_old_ok")
        assert resp.status_code == 200
        highlights = resp.json()["highlights"]
        oldest = [h for h in highlights if h["label"] == "Conta mais antiga"]
        assert len(oldest) == 1
        assert oldest[0]["value"] == "Old Account"
        assert "2015" in oldest[0]["detail"]
