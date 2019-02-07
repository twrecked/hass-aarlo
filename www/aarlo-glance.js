
import { LitElement, html } from 'https://unpkg.com/@polymer/lit-element@^0.5.2/lit-element.js?module';


class AarloGlance extends LitElement {

	static get properties() {
		return {
			_hass: Object,
			_config: Object,
			_img: String,
		}
	}

	static get outerStyleTemplate() {
		return html`
		<style>
			ha-card {
				position: relative;
				min-height: 48px;
				overflow: hidden;
			}
			hui-image.clickable {
				cursor: pointer;
			}
			.box {
				white-space: var(--paper-font-common-nowrap_-_white-space); overflow: var(--paper-font-common-nowrap_-_overflow); text-overflow: var(--paper-font-common-nowrap_-_text-overflow);
					position: absolute;
					left: 0;
					right: 0;
					bottom: 0;
					background-color: rgba(0, 0, 0, 0.4);
					padding: 4px 8px;
					font-size: 16px;
					line-height: 40px;
					color: white;
					display: flex;
					justify-content: space-between;
			}
			.middle {
				left: 10%;
				right: 10%;
				bottom: 35%;
			}
			.box .title {
				font-weight: 500;
				margin-left: 4px;
			}
			.box .status {
				font-weight: 500;
				margin-right: 4px;
				text-transform: capitalize;
			}
			ha-icon {
				cursor: pointer;
				padding: 2px;
				color: #a9a9a9;
			}
			ha-icon.state-update {
				color: #cccccc;
			}
			ha-icon.state-on {
				color: white;
			}
			ha-icon.state-warn {
				color: orange;
			}
			ha-icon.state-error {
				color: red;
			}
		</style>
		`;
	}

	static get innerStyleTemplate() {
		return html`
			<style>
				img {
					display: block;
					height: auto;
					transition: filter 0.2s linear;
					width: 100%;
				}
				.error {
					text-align: center;
				}
				.hidden {
					display: none;
				}
				.ratio {
					position: relative;
					width: 100%;
					height: 0;
				}
				.ratio img,
				.ratio div {
					position: absolute;
					top: 0;
					left: 0;
					width: 100%;
					height: 100%;
				}
				#brokenImage {
					background: grey url("/static/images/image-broken.svg") center/36px
					no-repeat;
				}
			</style>
		`;
	}

	_render( { _hass,_config } ) {

		const camera = _hass.states[this._cameraId];
		const cameraName = _config.name ? _config.name : camera.attributes.friendly_name;

		// do we have a valid image?
		var imageHidden = this._img != null ? '':'hidden';
		var brokeHidden = this._img == null ? '':'hidden';

		// what are we showing?
		var show = _config.show || [];
		var batteryHidden  = show.includes('battery') ? '' : 'hidden';
		var signalHidden   = show.includes('signal_strength') ? '' : 'hidden';
		var motionHidden   = show.includes('motion') ? '' : 'hidden';
		var soundHidden    = show.includes('sound') ? '' : 'hidden';
		var capturedHidden = show.includes('captured') ? '' : 'hidden';

		if( batteryHidden == '' ) {
			var battery      = _hass.states[this._batteryId];
			var batteryText  = 'Battery Strength: ' + battery.state +'%';
			var batteryIcon  = battery.state < 10 ? 'battery-outline' :
								( battery.state > 90 ? 'battery' : 'battery-' + Math.round(battery.state/10) +'0' );
			var batteryState = battery.state < 25 ? 'state-warn' :
								( battery.state < 15 ? 'state-error' : 'state-update' );
		} else {
			var batteryText  = 'not-used';
			var batteryIcon  = 'not-used';
			var batteryState = 'state-update';
		}

		if( signalHidden == '' ) {
			var signal      = _hass.states[this._signalId];
			var signal_text = 'Signal Strength: ' + signal.state;
			var signalIcon  = signal.state == 0 ? 'mdi:wifi-outline' : 'mdi:wifi-strength-' + signal.state;
		} else {
			var signal_text = 'not-used';
			var signalIcon  = 'mdi:wifi-strength-4';
		}

		if( motionHidden == '' ) {
			var motionOn   = _hass.states[this._motionId].state == 'on' ? 'state-on' : '';
			var motionText = 'Motion: ' + (motionOn != '' ? 'detected' : 'clear');
		} else {
			var motionOn   = 'not-used';
			var motionText = 'not-used';
		}

		if( soundHidden == '' ) {
			var soundOn    = _hass.states[this._soundId].state == 'on' ? 'state-on' : '';
			var soundText  = 'Sound: ' + (soundOn != '' ? 'detected' : 'clear');
			var capturedOn = 'state-update'
		} else {
			var soundOn    = 'not-used'
			var soundText  = 'not-used'
			var capturedOn = ''
		}

		if( capturedHidden == '' ) {
			var captured  = _hass.states[this._captureId].state;
			var last      = _hass.states[this._lastId].state;
			var last_text = 'Captured: ' + ( captured == 0 ? 'nothing today' :
												'today ' + captured + ',last at ' + last )
		} else {
			var last_text = 'not-used';
		}

		var img = html`
			${AarloGlance.innerStyleTemplate}
			<div id="wrapper">
				<img class$="${imageHidden}" id="image" src="${this._img}" />
				<div class$="${brokeHidden}" style="height: 100px" id="brokenImage"></div>
			</div>
		`;

		var state = html`
			<div class="box">
				<div class="title">
				${cameraName} 
				</div>
				<div>
					<ha-icon on-click="${(e) => { this.moreInfo(this._motionId); }}" class$="${motionOn} ${motionHidden}" icon="mdi:run-fast" title="${motionText}"></ha-icon>
					<ha-icon on-click="${(e) => { this.moreInfo(this._soundId); }}" class$="${soundOn} ${soundHidden}" icon="mdi:ear-hearing" title="${soundText}"></ha-icon>
					<ha-icon on-click="${(e) => { this.moreInfo(this._cameraId); }}" class$="${capturedOn} ${capturedHidden}" icon="mdi:file-video" title="${last_text}"></ha-icon>
					<ha-icon on-click="${(e) => { this.moreInfo(this._batteryId); }}" class$="${batteryState} ${batteryHidden}" icon="mdi:${batteryIcon}" title="${batteryText}"></ha-icon>
					<ha-icon on-click="${(e) => { this.moreInfo(this._signalId); }}" class$="state-update ${signalHidden}" icon="${signalIcon}" title="${signal_text}"></ha-icon>
				</div>
				<div class="status">
					${camera.state}
				</div>
			</div>
		`;

		return html`
			${AarloGlance.outerStyleTemplate}
			<ha-card>
			${img}
			${state}
			</ha-card>
		`;
	}

	set hass( hass ) {
		this._hass = hass
		this._updateCameraImageSrc()
	}

    setConfig(config) {

        if( !config.camera ) {
            throw new Error( 'missing a camera' )
        }
        if( !config.show ) {
            throw new Error( 'missing a show' )
        }

        this._config = config;
		this._cameraId  = 'camera.aarlo_' + config.camera;
		this._motionId  = 'binary_sensor.aarlo_motion_' + config.camera;
		this._soundId   = 'binary_sensor.aarlo_sound_' + config.camera;
		this._batteryId = 'sensor.aarlo_battery_level_' + config.camera;
		this._signalId  = 'sensor.aarlo_signal_strength_' + config.camera;
		this._captureId = 'sensor.aarlo_captured_today_' + config.camera;
		this._lastId    = 'sensor.aarlo_last_' + config.camera;

		this._updateCameraImageSrc()
    }

	moreInfo( id ) {
        const event = new Event('hass-more-info', {
          bubbles: true,
          cancelable: false,
          composed: true,
        });
        event.detail = { entityId: id };
        this.shadowRoot.dispatchEvent(event);
        return event;
	}


	async _updateCameraImageSrc() {
		try {
			const { content_type: contentType, content } = await this._hass.callWS({
				type: "camera_thumbnail",
				entity_id: this._cameraId,
			});
			this._img = `data:${contentType};base64, ${content}`;
		} catch (err) {
			this._img = null
		}
	}

    getCardSize() {
        return 3;
    }
}

customElements.define('aarlo-glance', AarloGlance);

