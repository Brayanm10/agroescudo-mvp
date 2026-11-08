"""Authorized views over real legacy and canonical telemetry; no synthetic data."""
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, exists, func, literal, or_, select, union_all
from sqlalchemy.orm import Session

from app.domain.metric_registry import METRICS_BY_CODE
from app.models import Alert, Company, Device, DeviceChannel, MetricDefinition, MetricReading, SensorReading, Site, StorageUnit, TelemetryEvent, User
from app.partner_models import PartnerGrant, PartnerOrganization, PartnerProducer
from app.services.device_capabilities import channel_metric_codes
from app.services.partner_security import PartnerError, aware, cursor_decode, cursor_encode, digest, now, public_id, require_scope

METRICS = {
    'GRAIN_TEMPERATURE_C': ('grain_temperature', 'grain_temp_1', 'degC'),
    'AMBIENT_TEMPERATURE_C': ('ambient_temperature', 'ambient_temp_1', 'degC'),
    'AMBIENT_RELATIVE_HUMIDITY_PCT': ('ambient_humidity', 'ambient_rh_1', 'percent'),
}


@dataclass
class Context:
    db: Session
    actor: object
    org: PartnerOrganization
    producer: PartnerProducer
    grants: list[PartnerGrant]
    units: list[StorageUnit]

    def binding(self, operation, filters):
        grants = [(g.id, g.storage_unit_id, g.device_id, g.channel_key, str(g.valid_from), str(g.expires_at)) for g in self.grants]
        return digest(json.dumps([self.actor.client.id, self.org.id, self.producer.id, grants, operation, filters], sort_keys=True))


def context(db, actor, org_id, producer_id, scope):
    require_scope(actor, scope)
    org = db.scalar(select(PartnerOrganization).join(Company, Company.id == PartnerOrganization.company_id).where(
        PartnerOrganization.client_id == actor.client.id, PartnerOrganization.external_id == org_id,
        PartnerOrganization.revoked_at.is_(None), Company.deleted_at.is_(None), Company.is_active.is_(True)))
    producer = db.scalar(select(PartnerProducer).where(PartnerProducer.organization_id == org.id, PartnerProducer.external_id == producer_id, PartnerProducer.revoked_at.is_(None))) if org else None
    if not org or not producer:
        raise PartnerError(403, 'FORBIDDEN')
    if producer.user_id:
        user = db.get(User, producer.user_id)
        if not user or not user.is_active or user.deleted_at or user.company_id != org.company_id or user.status != 'ACTIVE':
            raise PartnerError(403, 'FORBIDDEN')
    stamp = now()
    grants = list(db.scalars(select(PartnerGrant).where(
        PartnerGrant.producer_id == producer.id, PartnerGrant.revoked_at.is_(None), PartnerGrant.valid_from <= stamp,
        or_(PartnerGrant.expires_at.is_(None), PartnerGrant.expires_at > stamp)).order_by(PartnerGrant.id).limit(1001)).all())
    if len(grants) > 1000:
        raise PartnerError(503, 'SERVICE_UNAVAILABLE')
    units = list(db.scalars(select(StorageUnit).join(Site, Site.id == StorageUnit.site_id).where(
        StorageUnit.id.in_({g.storage_unit_id for g in grants}), StorageUnit.company_id == org.company_id,
        Site.company_id == org.company_id, StorageUnit.deleted_at.is_(None), StorageUnit.is_active.is_(True),
        StorageUnit.operation_type == 'storage')).all())
    unit_ids = {u.id for u in units}
    grants = [g for g in grants if g.storage_unit_id in unit_ids]
    return Context(db, actor, org, producer, grants, units)


def unit_for(ctx, opaque):
    unit = next((u for u in ctx.units if public_id('su', u.id) == opaque), None)
    if unit is None:
        raise PartnerError(404, 'RESOURCE_NOT_FOUND')
    return unit


def permitted_devices(ctx, unit):
    grants = [g for g in ctx.grants if g.storage_unit_id == unit.id]
    unrestricted = any(g.device_id is None for g in grants)
    stmt = select(Device).where(Device.storage_unit_id == unit.id, Device.company_id == ctx.org.company_id, Device.site_id == unit.site_id, Device.deleted_at.is_(None))
    if not unrestricted:
        stmt = stmt.where(Device.id.in_({g.device_id for g in grants}))
    devices = list(ctx.db.scalars(stmt.order_by(Device.id).limit(101)).all())
    if len(devices) > 100:
        raise PartnerError(400, 'RESPONSE_TOO_LARGE', 'Acotar concesión a un máximo de 100 dispositivos por unidad.')
    return devices


def pairs_for(ctx, unit, devices):
    result = []
    for device in devices:
        gs = [g for g in ctx.grants if g.storage_unit_id == unit.id and g.device_id in (None, device.id)]
        rows = list(ctx.db.scalars(select(DeviceChannel).where(DeviceChannel.device_id == device.id).limit(101)).all())
        if len(rows) > 100:
            raise PartnerError(400, 'RESPONSE_TOO_LARGE')
        if rows:
            for ch in rows:
                if not ch.is_active or not ch.is_installed or not ch.is_enabled or not ch.is_visible_to_client or ch.retired_at:
                    continue
                if not any(g.channel_key in (None, ch.channel_key) for g in gs):
                    continue
                for code in channel_metric_codes(ch):
                    if code in METRICS:
                        result.append((device.id, ch.channel_key, code, ch.id))
        else:
            # Older installations without channel metadata: advertise only fields
            # actually observed, with the registry's unambiguous legacy mapping.
            for code, (field, channel, _) in METRICS.items():
                if any(g.channel_key in (None, channel) for g in gs) and ctx.db.scalar(select(SensorReading.id).where(
                    SensorReading.device_id == device.id, SensorReading.storage_unit_id == unit.id,
                    SensorReading.company_id == ctx.org.company_id, SensorReading.site_id == unit.site_id,
                    getattr(SensorReading, field).is_not(None)).limit(1)):
                    result.append((device.id, channel, code, None))
    if len(result) > 300:
        raise PartnerError(400, 'RESPONSE_TOO_LARGE')
    return result


def device_out(device, pairs, stamp):
    cadence = device.expected_reading_interval_minutes
    interval = cadence*60 if cadence and cadence > 0 else None
    cutoff = interval*3 if interval else None
    seen = aware(device.last_seen_at) if device.last_seen_at else None
    state = 'inactive' if not device.is_active else 'unknown'
    if device.is_active and seen and cutoff and seen <= stamp+timedelta(minutes=5):
        state = 'online' if (stamp-seen).total_seconds() <= cutoff else 'offline'
    return {'id': public_id('dev', device.id), 'status': state, 'last_seen_at': seen,
            'expected_interval_seconds': interval, 'offline_after_seconds': cutoff,
            'capabilities': [{'channel_key': c, 'metric_code': m, 'unit': METRICS[m][2]} for d,c,m,_ in pairs if d == device.id]}


def window(from_, to, required=True):
    if from_ is None and to is None and not required:
        return
    if from_ is None or to is None or from_.tzinfo is None or to.tzinfo is None:
        raise PartnerError(400, 'INVALID_REQUEST', 'Enviar from y to con zona horaria UTC.')
    if from_.utcoffset() != timedelta(0) or to.utcoffset() != timedelta(0) or from_ >= to or to-from_ > timedelta(days=31):
        raise PartnerError(400, 'INVALID_REQUEST', 'El intervalo UTC [from,to) debe ser positivo y de hasta 31 días.')


def page_state(ctx, operation, filters, cursor):
    binding = ctx.binding(operation, filters)
    if cursor:
        data = cursor_decode(cursor, binding)
        return binding, data['snapshot'], data['position']
    snapshot = {'at': now().isoformat(), 'canonical': ctx.db.scalar(select(func.max(MetricReading.id))) or 0,
                'legacy': ctx.db.scalar(select(func.max(SensorReading.id))) or 0,
                'alerts': ctx.db.scalar(select(func.max(Alert.id))) or 0}
    return binding, snapshot, None


def observation_query(ctx, unit, devices, pairs, snapshot):
    parts=[]
    device_ids={d.id for d in devices if d.is_active}
    pairs=[p for p in pairs if p[0] in device_ids]
    canon_pairs=[and_(MetricReading.device_id==d, MetricReading.sensor_channel_id==cid, MetricReading.metric_code==m) for d,c,m,cid in pairs if cid]
    if canon_pairs:
        parts.append(select(literal('c').label('source'), MetricReading.id.label('row_id'), MetricReading.device_id.label('device_id'), DeviceChannel.channel_key.label('channel_key'),
            MetricReading.metric_code.label('metric_code'), func.coalesce(MetricReading.display_value, MetricReading.calibrated_value, MetricReading.raw_value).label('value'),
            MetricReading.canonical_unit.label('unit'), MetricReading.sampled_at.label('sampled_at'), MetricReading.received_at.label('received_at'), MetricReading.quality_status.label('quality_status')).join(
                DeviceChannel, DeviceChannel.id==MetricReading.sensor_channel_id).join(TelemetryEvent, TelemetryEvent.id==MetricReading.telemetry_event_id).join(MetricDefinition, MetricDefinition.id==MetricReading.metric_definition_id).where(
            or_(*canon_pairs), MetricReading.id<=snapshot['canonical'], MetricReading.received_at<=datetime.fromisoformat(snapshot['at']), MetricReading.company_id==ctx.org.company_id, MetricReading.storage_unit_id==unit.id,
            TelemetryEvent.company_id==ctx.org.company_id, TelemetryEvent.storage_unit_id==unit.id, TelemetryEvent.device_id==MetricReading.device_id,
            MetricDefinition.metric_code==MetricReading.metric_code, MetricDefinition.client_visibility.is_(True), MetricDefinition.is_derived.is_(False)))
    for d,channel,code,cid in pairs:
        field,legacy_channel,unit_name=METRICS[code]
        if channel != legacy_channel:
            continue  # Never project one legacy field onto multiple physical channels.
        duplicate = exists(select(MetricReading.id).join(TelemetryEvent, TelemetryEvent.id==MetricReading.telemetry_event_id).where(
            TelemetryEvent.sensor_reading_id==SensorReading.id, MetricReading.device_id==d, MetricReading.metric_code==code,
            MetricReading.sensor_channel_id==cid, MetricReading.id<=snapshot['canonical'])) if cid else literal(False)
        parts.append(select(literal('l').label('source'), SensorReading.id.label('row_id'), SensorReading.device_id.label('device_id'), literal(channel).label('channel_key'),
            literal(code).label('metric_code'), getattr(SensorReading,field).label('value'), literal(unit_name).label('unit'),
            SensorReading.timestamp.label('sampled_at'), SensorReading.received_at.label('received_at'), literal('UNKNOWN').label('quality_status')).where(
            SensorReading.device_id==d, SensorReading.company_id==ctx.org.company_id, SensorReading.site_id==unit.site_id,
            SensorReading.storage_unit_id==unit.id, SensorReading.id<=snapshot['legacy'], SensorReading.received_at<=datetime.fromisoformat(snapshot['at']), getattr(SensorReading,field).is_not(None), ~duplicate))
    return union_all(*parts).subquery() if parts else None


def observation_out(row, device, stamp):
    code = row.metric_code
    spec = METRICS_BY_CODE[code]
    value = row.value
    sampled, received = aware(row.sampled_at), aware(row.received_at)
    raw_quality = row.quality_status.upper()
    invalid = value is None or not math.isfinite(value) or not (spec.physical_min<=value<=spec.physical_max) or row.unit!=METRICS[code][2] or sampled>stamp+timedelta(minutes=5) or sampled>received+timedelta(minutes=5) or any(x in raw_quality for x in ['INVALID','REJECT','QUARANTINE','OUT_OF_RANGE','ERROR'])
    quality = 'invalid' if invalid else ('uncalibrated' if 'UNCALIBRATED' in raw_quality else ('valid' if raw_quality in {'VALID','CALIBRATED','LEGACY_REPORTED'} else 'unknown'))
    cadence = device.expected_reading_interval_minutes
    threshold = cadence*180 if cadence and cadence>0 else None
    return {'reading_id':public_id('rd', f'{row.source}:{row.row_id}:{row.channel_key}:{code}'), 'device_id':public_id('dev',device.id),
            'channel_key':row.channel_key,'metric_code':code,'value':None if invalid else value,'unit':METRICS[code][2],
            'sampled_at':sampled,'received_at':received,'quality_status':quality,'stale_after_seconds':threshold,
            'is_stale': (stamp-sampled).total_seconds()>threshold if threshold else None}


def catalogue(ctx, limit, cursor):
    binding,snapshot,position=page_state(ctx,'units',{'limit':limit},cursor)
    units=sorted(ctx.units,key=lambda u:public_id('su',u.id))
    if position:units=[u for u in units if public_id('su',u.id)>position]
    output=[]
    for u in units[:limit]:
        devices=permitted_devices(ctx,u);pairs=pairs_for(ctx,u,devices)
        output.append({'id':public_id('su',u.id),'name':u.name,'operation_type':'storage','unit_type':u.unit_type,
                       'devices':[device_out(d,pairs,now()) for d in devices]})
    return {'items':output,'next_cursor':cursor_encode(binding,output[-1]['id'],snapshot) if len(units)>limit else None}


def observations(ctx, opaque, latest=False, from_=None, to=None, device_id=None, metric_code=None, channel_key=None, limit=100, cursor=None):
    unit=unit_for(ctx,opaque);devices=permitted_devices(ctx,unit);pairs=pairs_for(ctx,unit,devices)
    if device_id:
        devices=[d for d in devices if public_id('dev',d.id)==device_id]
        if not devices:raise PartnerError(404,'RESOURCE_NOT_FOUND')
    filters={'unit':opaque,'from':from_.isoformat() if from_ else None,'to':to.isoformat() if to else None,'device':device_id,'metric':metric_code,'channel':channel_key,'limit':limit}
    binding,snapshot,position=page_state(ctx,'latest' if latest else 'readings',filters,cursor)
    stamp=now();rows=[]
    q = None if latest else observation_query(ctx,unit,devices,pairs,snapshot)
    if latest:
        # Bounded indexed top-1 per authorized series, instead of ranking the
        # complete historical union for every dashboard refresh.
        for pair in pairs:
            series=observation_query(ctx,unit,devices,[pair],snapshot)
            if series is not None:
                row=ctx.db.execute(select(series).order_by(series.c.sampled_at.desc(),series.c.source.asc(),series.c.row_id.desc()).limit(1)).first()
                if row is not None:rows.append(row)
        rows.sort(key=lambda row:(row.device_id,row.channel_key,row.metric_code))
    elif q is not None:
        query=select(q)
        if from_:query=query.where(q.c.sampled_at>=from_,q.c.sampled_at<to)
        if metric_code:query=query.where(q.c.metric_code==metric_code)
        if channel_key:query=query.where(q.c.channel_key==channel_key)
        if position:
            ts=datetime.fromisoformat(position[0]);source=position[1];rid=position[2];channel=position[3];metric=position[4]
            from sqlalchemy import tuple_
            query=query.where(tuple_(q.c.sampled_at,q.c.source,q.c.row_id,q.c.channel_key,q.c.metric_code)>tuple_(ts,source,rid,channel,metric))
        rows=ctx.db.execute(query.order_by(q.c.sampled_at,q.c.source,q.c.row_id,q.c.channel_key,q.c.metric_code).limit(limit+1)).all()
    by_id={d.id:d for d in devices}
    selected=rows if latest else rows[:limit]
    output=[observation_out(r,by_id[r.device_id],stamp) for r in selected]
    if latest:
        if len(output)>300:raise PartnerError(400,'RESPONSE_TOO_LARGE')
        return {'storage_unit_id':opaque,'generated_at':stamp,'devices':[device_out(d,pairs,stamp) for d in devices],'items':output}
    next_cursor=None
    if len(rows)>limit:
        r=selected[-1];pos=[aware(r.sampled_at).isoformat(),r.source,r.row_id,r.channel_key,r.metric_code]
        next_cursor=cursor_encode(binding,pos,snapshot)
    return {'items':output,'next_cursor':next_cursor}


def alerts(ctx, opaque, from_, to, device_id, status, severity, limit, cursor):
    unit=unit_for(ctx,opaque);devices=permitted_devices(ctx,unit);pairs=pairs_for(ctx,unit,devices)
    if device_id:
        devices=[d for d in devices if public_id('dev',d.id)==device_id]
        if not devices:raise PartnerError(404,'RESOURCE_NOT_FOUND')
    ids={d.id for d in devices}
    allowed=[]
    for d,c,code,cid in pairs:
        if d not in ids:continue
        field,_,_=METRICS[code]
        # Channel-less legacy alert can only be projected onto its unique legacy
        # channel. Explicit canonical alert channels must match the grant.
        legacy=and_(Alert.sensor_channel_id.is_(None),Alert.metric.in_([field,code])) if c==METRICS[code][1] else literal(False)
        canonical=and_(Alert.sensor_channel_id==cid,Alert.metric.in_([field,code])) if cid else literal(False)
        allowed.append(and_(Alert.device_id==d,or_(legacy,canonical)))
    filters={'unit':opaque,'from':from_.isoformat() if from_ else None,'to':to.isoformat() if to else None,'device':device_id,'status':status,'severity':severity,'limit':limit}
    binding,snapshot,position=page_state(ctx,'alerts',filters,cursor)
    stmt=select(Alert).where(Alert.company_id==ctx.org.company_id,Alert.site_id==unit.site_id,Alert.storage_unit_id==unit.id,Alert.id<=snapshot['alerts'],or_(*allowed) if allowed else literal(False))
    if from_:stmt=stmt.where(Alert.created_at>=from_,Alert.created_at<to)
    if status=='resolved':stmt=stmt.where(Alert.is_active.is_(False))
    elif status=='acknowledged':stmt=stmt.where(Alert.is_active.is_(True),Alert.acknowledged_at.is_not(None))
    elif status=='active':stmt=stmt.where(Alert.is_active.is_(True),Alert.acknowledged_at.is_(None))
    if severity:stmt=stmt.where(Alert.severity==severity)
    if position:stmt=stmt.where(or_(Alert.created_at<datetime.fromisoformat(position[0]),and_(Alert.created_at==datetime.fromisoformat(position[0]),Alert.id<position[1])))
    rows=list(ctx.db.scalars(stmt.order_by(Alert.created_at.desc(),Alert.id.desc()).limit(limit+1)).all())
    output=[]
    reverse={field:code for code,(field,_,_) in METRICS.items()}
    for a in rows[:limit]:
        code=reverse.get(a.metric,a.metric)
        output.append({'id':public_id('al',a.id),'storage_unit_id':opaque,'device_id':public_id('dev',a.device_id),'metric_code':code,
                       'severity':a.severity if a.severity in ['warning','critical','technical'] else 'unknown',
                       'status':'resolved' if not a.is_active else 'acknowledged' if a.acknowledged_at else 'active',
                       # Do not expose free-form internal notes or personal data.
                       'message':'Alerta de monitoreo: '+code,
                       'observed_value':a.observed_value if a.observed_value is not None and math.isfinite(a.observed_value) else None,
                       'threshold_value':a.threshold_value if a.threshold_value is not None and math.isfinite(a.threshold_value) else None,
                       'unit':METRICS[code][2],'created_at':aware(a.created_at),'resolved_at':aware(a.resolved_at) if a.resolved_at else None})
    return {'items':output,'next_cursor':cursor_encode(binding,[aware(rows[limit-1].created_at).isoformat(),rows[limit-1].id],snapshot) if len(rows)>limit else None}
