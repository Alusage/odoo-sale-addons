odoo.define('sale_order_subscription_payment_stripe.payment_form', function (require) {
    "use strict";

    var core = require('web.core');
    var PaymentForm = require('payment.payment_form');

    var _t = core._t;

    PaymentForm.include({

        _createStripeToken: function (ev, $checkedRadio, addPmEvent) {
            var self = this;
            if (ev.type === 'submit') {
                var button = $(ev.target).find('*[type="submit"]')[0]
            } else {
                var button = ev.target;
            }
            this.disableButton(button);
            var acquirerID = this.getAcquirerIdFromRadio($checkedRadio);
            var acquirerForm = this.$('#o_payment_add_token_acq_' + acquirerID);
            var inputsForm = $('input', acquirerForm);
            if (this.options.partnerId === undefined) {
                console.warn('payment_form: unset partner_id when adding new token; things could go wrong');
            }

            var formData = self.getFormData(inputsForm);
            var stripe = this.stripe;
            var card = this.stripe_card_element;
            if (card._invalid) {
                return;
            }
            return this._rpc({
                route: '/payment/stripe/s2s/create_setup_intent',
                params: {'acquirer_id': formData.acquirer_id}
            }).then(function(intent_secret){
                return stripe.confirmCardSetup(intent_secret,
                        {
                            payment_method: {
                                card: card,
                            },
                        }
                    );
            }).then(function(result) {
                if (result.error) {
                    return Promise.reject({"message": {"data": { "arguments": [result.error.message]}}});
                } else {
                    _.extend(formData, {"payment_method": result.setupIntent.payment_method});
                    return self._rpc({
                        route: formData.data_set,
                        params: formData,
                    })
                }
            }).then(function(result) {
                if (addPmEvent) {
                    if (formData.return_url) {
                        window.location = formData.return_url;
                    } else {
                        window.location.reload();
                    }
                } else {
                    $checkedRadio.val(result.id);
                    self.el.submit();
                }
            }).guardedCatch(function (error) {
                // We don't want to open the Error dialog since
                // we already have a container displaying the error
                //error.event.preventDefault();
                // if the rpc fails, pretty obvious
                self.enableButton(button);
                self.displayError(
                    _t('Unable to save card'),
                    _t("We are not able to add your payment method at the moment. ") +
                        self._parseError(error)
                );
            });
        },
    });
});
