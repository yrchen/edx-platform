/**
 * A generic card view class.
 *
 * Subclasses must implement:
 * - action (function): Action to take when the action text is clicked.
 */
;(function (define) {
    'use strict';
    define(['backbone', 'text!templates/components/card/card.underscore', 'text!templates/components/card/list-item.underscore'],
        function (Backbone, cardTemplate, listItemTemplate) {
            var CardView = Backbone.View.extend({
                events: {
                    'click .action' : 'action'
                },

                initialize: function (options) {
                    var configuration = options.configuration || 'card';
                    this.template = configuration == 'card' ? _.template(cardTemplate) : _.template(listItemTemplate);
                    this.listenTo(this.model, 'change', this.render);
                    this.render();
                },

                render: function () {
                    var json = this.model.attributes;
                    this.$el.html(this.template(_.defaults(json, {right_item: ''})));
                    return this;
                }
            });

            return CardView;
        });
}).call(this, define || RequireJS.define);
