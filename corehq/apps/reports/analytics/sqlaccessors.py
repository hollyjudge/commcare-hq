from django.db.models.aggregates import Count

from corehq.apps.sofabed.models import FormData


def get_form_counts_for_user_by_date(user_ids, startdate, enddate, date_field, timezone):
    assert len(user_ids) > 0

    if len(user_ids) == 1:
        results = FormData.objects.filter(user_id=user_ids[0])
    else:
        results = FormData.objects.filter(user_id__in=user_ids)

    results = results.filter(**{'%s__range' % date_field: (startdate, enddate)}) \
        .extra({'date': "date(%s AT TIME ZONE '%s')" % (date_field, timezone)}) \
        .values('date') \
        .annotate(Count(date_field))
    return results


def get_form_counts_for_daterange_by_user(startdate, enddate, date_field):
    results = FormData.objects \
        .filter(**{'%s__range' % date_field: (startdate, enddate)}) \
        .values('user_id') \
        .annotate(Count('user_id'))
    return results
