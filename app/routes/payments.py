import stripe
from flask import Blueprint, redirect, url_for, flash, request, render_template, current_app, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.course import Course, Purchase

payments_bp = Blueprint("payments", __name__)


# ── Tutor: Stripe Connect (Express) onboarding ────────────────────────────────
@payments_bp.route("/connect/onboarding")
@login_required
def connect_onboarding():
    """Kick off (or resume) Stripe Express onboarding for a tutor who wants to sell courses."""
    if not current_user.is_tutor():
        flash("Yalnız müəllimlər üçündür.", "error")
        return redirect(url_for("main.dashboard"))

    profile = current_user.tutor_profile
    if not profile:
        flash("Müəllim profili tapılmadı.", "error")
        return redirect(url_for("main.dashboard"))

    domain = current_app.config["DOMAIN"]

    try:
        if not profile.stripe_account_id:
            account = stripe.Account.create(
                type="express",
                email=current_user.email,
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
            )
            profile.stripe_account_id = account.id
            db.session.commit()

        account_link = stripe.AccountLink.create(
            account=profile.stripe_account_id,
            refresh_url=f"{domain}{url_for('payments.connect_onboarding')}",
            return_url=f"{domain}{url_for('payments.connect_return')}",
            type="account_onboarding",
        )
        return redirect(account_link.url)

    except stripe.error.StripeError as e:
        flash(f"Stripe xətası: {e.user_message or str(e)}", "error")
        return redirect(url_for("main.dashboard"))


@payments_bp.route("/connect/return")
@login_required
def connect_return():
    """User lands here after finishing (or leaving) Stripe onboarding."""
    profile = current_user.tutor_profile
    if not profile:
        flash("Müəllim profili tapılmadı.", "error")
        return redirect(url_for("main.dashboard"))

    if profile.stripe_account_id:
        try:
            account = stripe.Account.retrieve(profile.stripe_account_id)
            profile.stripe_onboarding_complete = bool(account.details_submitted and account.charges_enabled)
            db.session.commit()
        except stripe.error.StripeError:
            pass

    if profile.stripe_onboarding_complete:
        flash("Ödəniş hesabınız uğurla qoşuldu! İndi ödənişli kurslar yarada bilərsiniz.", "success")
    else:
        flash("Qeydiyyat tamamlanmadı. Zəhmət olmasa yenidən cəhd edin.", "info")

    return redirect(url_for("courses.my_courses"))


# ── Student: Checkout ──────────────────────────────────────────────────────────
@payments_bp.route("/checkout/<int:course_id>", methods=["POST"])
@login_required
def create_checkout(course_id):
    if current_user.is_tutor():
        flash("Müəllimlər kurs ala bilməz.", "error")
        return redirect(url_for("courses.detail", course_id=course_id))

    course = Course.query.get_or_404(course_id)
    if not course.is_published:
        flash("Bu kurs mövcud deyil.", "error")
        return redirect(url_for("courses.browse"))

    if course.is_purchased_by(current_user.id):
        flash("Siz artıq bu kursu almısınız.", "info")
        return redirect(url_for("courses.detail", course_id=course_id))

    # ── Free course: skip Stripe entirely, no need for the tutor to be
    #    Stripe-connected since no money changes hands. ─────────────────────
    if course.is_free:
        purchase = Purchase.query.filter_by(course_id=course.id, student_id=current_user.id).first()
        if purchase:
            purchase.amount_azn = 0
            purchase.platform_fee_azn = 0
            purchase.status = "completed"
        else:
            purchase = Purchase(
                course_id=course.id,
                student_id=current_user.id,
                amount_azn=0,
                platform_fee_azn=0,
                status="completed",
            )
            db.session.add(purchase)
        db.session.commit()
        flash("Kursa qoşuldunuz!", "success")
        return redirect(url_for("courses.detail", course_id=course_id))

    tutor_profile = course.tutor.tutor_profile
    if not tutor_profile or not tutor_profile.can_sell_courses():
        flash("Bu müəllim hələ ödəniş qəbul edə bilmir.", "error")
        return redirect(url_for("courses.detail", course_id=course_id))

    domain = current_app.config["DOMAIN"]
    price_cents = int(float(course.price_azn) * 100)
    fee_percent = current_app.config["PLATFORM_FEE_PERCENT"]
    platform_fee_cents = int(price_cents * fee_percent / 100)

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "azn",
                    "product_data": {"name": course.title},
                    "unit_amount": price_cents,
                },
                "quantity": 1,
            }],
            payment_intent_data={
                "application_fee_amount": platform_fee_cents,
                "transfer_data": {"destination": tutor_profile.stripe_account_id},
            },
            success_url=f"{domain}{url_for('payments.checkout_success')}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{domain}{url_for('courses.detail', course_id=course.id)}",
            metadata={"course_id": course.id, "student_id": current_user.id},
        )

        purchase = Purchase.query.filter_by(course_id=course.id, student_id=current_user.id).first()
        if purchase:
            purchase.amount_azn = course.price_azn
            purchase.platform_fee_azn = platform_fee_cents / 100
            purchase.stripe_checkout_session_id = session.id
            purchase.stripe_payment_intent_id = None
            purchase.status = "pending"
        else:
            purchase = Purchase(
                course_id=course.id,
                student_id=current_user.id,
                amount_azn=course.price_azn,
                platform_fee_azn=platform_fee_cents / 100,
                stripe_checkout_session_id=session.id,
                status="pending",
            )
            db.session.add(purchase)
        db.session.commit()

        return redirect(session.url, code=303)

    except stripe.error.StripeError as e:
        flash(f"Ödəniş xətası: {e.user_message or str(e)}", "error")
        return redirect(url_for("courses.detail", course_id=course_id))


@payments_bp.route("/checkout/success")
@login_required
def checkout_success():
    session_id = request.args.get("session_id")
    purchase = Purchase.query.filter_by(stripe_checkout_session_id=session_id).first()

    if purchase:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                purchase.status = "completed"
                purchase.stripe_payment_intent_id = session.payment_intent
                db.session.commit()
                flash("Ödəniş uğurlu oldu! Kurs sizə açıldı.", "success")
        except stripe.error.StripeError:
            pass

    return redirect(url_for("payments.my_purchases"))


@payments_bp.route("/webhook", methods=["POST"])
def webhook():
    """Stripe webhook — confirms payment server-side even if the user closes the tab."""
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = current_app.config["STRIPE_WEBHOOK_SECRET"]

    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            event = stripe.Event.construct_from(request.get_json(), stripe.api_key)
    except (ValueError, stripe.error.SignatureVerificationError):
        return jsonify({"error": "invalid payload"}), 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        purchase = Purchase.query.filter_by(stripe_checkout_session_id=session["id"]).first()
        if purchase and purchase.status != "completed":
            purchase.status = "completed"
            purchase.stripe_payment_intent_id = session.get("payment_intent")
            db.session.commit()

    return jsonify({"status": "ok"}), 200


# ── Student: My Courses dashboard ─────────────────────────────────────────────
@payments_bp.route("/my-courses")
@login_required
def my_purchases():
    purchases = (
        Purchase.query
        .filter_by(student_id=current_user.id, status="completed")
        .order_by(Purchase.created_at.desc())
        .all()
    )
    return render_template("courses/my_purchases.html", purchases=purchases)