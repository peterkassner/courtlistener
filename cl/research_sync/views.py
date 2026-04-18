from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cl.research_sync.models import LocalHit, SyncTarget


@login_required
def dashboard(request):
    targets = SyncTarget.objects.filter(enabled=True).order_by("name")
    unread = (
        LocalHit.objects.filter(is_read=False)
        .select_related("target")
        .order_by("-discovered_at")[:100]
    )
    return render(
        request,
        "research_sync/dashboard.html",
        {"targets": targets, "unread_hits": unread},
    )


@login_required
@require_POST
def mark_read(request, hit_id: int):
    hit = get_object_or_404(LocalHit, pk=hit_id)
    hit.is_read = True
    hit.save(update_fields=["is_read"])
    return redirect("research_sync:dashboard")
