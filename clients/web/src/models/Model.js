import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';

import { restRequest, getApiRoot } from 'girder/rest';

/**
 * All models should descend from this base model, which provides a number
 * of utilities for synchronization.
 */
var Model = Backbone.Model.extend({
    resourceName: null,
    altUrl: null,
    idAttribute: '_id',

    /**
     * Convenience method for incrementing numeric properties.
     * @param {string} attr The attribute to increment.
     * @param {number} [amount] The amount to increment by. Defaults to 1.
     */
    increment: function (attr, amount) {
        if (amount === undefined) {
            amount = 1;
        }
        if (!amount) {
            return;
        }
        return this.set(attr, this.get(attr) + amount);
    },

    /**
     * Get the name for this resource. By default, just the name attribute.
     */
    name: function () {
        return this.get('name');
    },

    /**
     * Save this model to the server. If this is a new model, meaning it has no
     * _id attribute, this will create it. If the _id is set, we update the
     * existing model. Triggers g:saved on success, and g:error on error.
     */
    save: function () {
        if (this.altUrl === null && this.resourceName === null) {
            throw new Error('An altUrl or resourceName must be set on the Model.');
        }

        var path, type;
        if (this.has('_id')) {
            path = (this.altUrl || this.resourceName) + '/' + this.get('_id');
            type = 'PUT';
        } else {
            path = (this.altUrl || this.resourceName);
            type = 'POST';
        }
        /* Don't save attributes which are objects using this call.  For
         * instance, if the metadata of an item has keys that contain non-ascii
         * values, they won't get handled by the rest call. */
        var data = {};
        _.each(this.keys(), function (key) {
            var value = this.get(key);
            if (!_.isObject(value)) {
                data[key] = value;
            }
        }, this);

        return restRequest({
            path: path,
            type: type,
            data: data,
            error: null // don't do default error behavior (validation may fail)
        }).done(_.bind(function (resp) {
            this.set(resp);
            this.trigger('g:saved');
        }, this)).fail(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    },

    /**
     * Fetch a single resource from the server. Triggers g:fetched on success,
     * or g:error on error.
     *
     * @param {object|undefined} opts: additional options, which can include:
     *     ignoreError: true - ignore the default error handler
     *     extraPath - a string to append to the end of the resource path
     *     data - a dictionary of parameters to pass to the endpoint.
     */
    fetch: function (opts) {
        if (this.altUrl === null && this.resourceName === null) {
            throw new Error('An altUrl or resourceName must be set on the Model.');
        }

        opts = opts || {};
        var restOpts = {
            path: (this.altUrl || this.resourceName) + '/' + this.get('_id')
        };
        if (opts.extraPath) {
            restOpts.path += '/' + opts.extraPath;
        }
        if (opts.ignoreError) {
            restOpts.error = null;
        }
        if (opts.data) {
            restOpts.data = opts.data;
        }
        return restRequest(restOpts).done((resp) => {
            this.set(resp);
            if (opts.extraPath) {
                this.trigger('g:fetched.' + opts.extraPath);
            } else {
                this.trigger('g:fetched');
            }
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    },

    /**
     * Get the path for downloading this resource via the API. Can be used
     * as the href property of a direct download link.
     * @param params {Object} list of key-value parameters to include in the
     *    query string.
     */
    downloadUrl: function (params) {
        let url = `${getApiRoot()}/${this.altUrl || this.resourceName}/${this.id}/download`;

        if (params) {
            url += '?' + $.param(params);
        }

        return url;
    },

    /**
     * For models that can be downloaded, this method can be used to
     * initiate the download in the browser.
     */
    download: function () {
        window.location.assign(this.downloadUrl());
    },

    /**
     * Delete the model on the server.
     * @param opts Options, may contain:
     *   throwError Whether to throw an error (bool, default=true)
     *   progress Whether to record progress (bool, default=false)
     */
    destroy: function (opts) {
        if (this.altUrl === null && this.resourceName === null) {
            throw new Error('An altUrl or resourceName must be set on the Model.');
        }

        var args = {
            path: (this.altUrl || this.resourceName) + '/' + this.get('_id'),
            type: 'DELETE'
        };

        opts = opts || {};
        if (opts.progress === true) {
            args.path += '?progress=true';
        }

        if (opts.throwError !== false) {
            args.error = null;
        }

        return restRequest(args).done(_.bind(function () {
            if (this.collection) {
                this.collection.remove(this);
            }
            this.trigger('g:deleted');
        }, this)).fail(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    },

    /**
     * Return the access level with respect to the current user
     */
    getAccessLevel: function () {
        return this.get('_accessLevel');
    }

});

export default Model;
